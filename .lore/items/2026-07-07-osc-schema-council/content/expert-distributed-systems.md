# Distributed-systems reality check — bopOS OSC contract

## 1. Lens & altitude

I care about one question: **what does the wire actually do at 50–100 nodes on a
network you don't own?** I read the code (`helper.py`, `io/main.py`, `start.sh`,
the port map) rather than the summaries. My altitude is mid: I take the settled
decisions as given and design the *identity, transport, and distribution
mechanics* underneath them — because that is where an elegant contract meets a
managed office switch and dies. I own seats C, E, G, H and the liveness story.

## 2. Problem reframing

Today's contract has three latent distributed-systems bugs that the "office
floor of live-booted boxes" scenario detonates:

1. **Identity is pre-registered MAC.** Unknown MAC → `id = -1`, no fallback.
   You cannot pre-register 50 office machines you've never seen. Worse, modern
   Linux/NetworkManager randomizes WiFi MAC per-SSID by default, so even a
   "known" box can change its MAC across boots.
2. **Identity is correlated by source IP at the dashboard.** IP comes from DHCP.
   Leases churn; a node that drops and rejoins gets a new IP and looks like a
   new device (or two). IP is a *return path*, never an identity.
3. **Everything Pi→laptop is UDP broadcast, and high-rate control is heading
   the same way.** WiFi sends broadcast/multicast at the lowest basic rate with
   **no ACK and no retransmit** — it is both slow and lossy. Managed switches
   rate-limit broadcast (storm control); APs with client-isolation drop
   station-to-station broadcast entirely. Broadcast is a scarce, unreliable
   resource, not a free bus.

The stateless live-image adds the twist: **nothing survives reboot on the
device.** So identity persistence cannot live on the node.

## 3. Proposed design

### Identity & assignment lifecycle (seat C)

Two layers, and the persistence lives at the **dashboard**, never on the box:

- **`uid` — the join key.** A stable-per-session token the device generates
  itself. On a Pi it *is* the MAC (backward compatible with the settled
  `/hb <mac> …`). On a live-image x86 box, derive it from a stable hardware
  source (`/etc/machine-id` if persisted, else primary-NIC MAC with
  randomization disabled, else DMI serial). The framework does not care what it
  is, only that the same physical box reports the same `uid` for the run.
- **Assignment — id, position(s), hostname, engine.** Held **at the dashboard**
  in a persistent `uid → assignment` table. `bopos.devices` becomes a *seed*
  for that table and the local fallback, not the source of truth.

Lifecycle:

```
device boot → broadcast /os/hello <uid> <engine> <caps>   (every ~2s until assigned)
dashboard   → look up uid:
               known   → /os/assign <uid> <id> <posL> <posR> <hostname>
               unknown → show "unassigned box, RSSI x, blink LED" → operator assigns → same /os/assign
device      → apply in RAM, drop to 10s heartbeat. Stores NOTHING.
reboot      → re-hello → dashboard re-pushes the same /os/assign.
```

The load-bearing property: **`/os/assign` is idempotent full-state keyed by
`uid`.** Re-sending it never duplicates or corrupts a state change, because it
is an absolute assignment, not a delta. That is *why* it can ride lossy
broadcast and be re-sent freely. This must be the rule for the whole framework
control plane: full-state and idempotent (gain already is), so "just re-send to
be sure" is always safe. No fleet-wide command may be an increment.

No-dashboard fallback: unknown `uid` with no assignment stays at the existing
`id = -1` and heartbeats as unassigned — fail loud, reuse the current
convention. `bopos.devices` still works for autonomous Pi installs.

### Liveness / telemetry

Heartbeat from helper.py (settled), extended one field:
`/hb <uid> <id> <version> <engine-alive 0|1> [rssi]`, broadcast on the up-port
every 10s. The `engine-alive` flag lets the dashboard distinguish "box up,
engine crashed" (silent speaker) from "box fell off WiFi" — the two failures an
artist must tell apart mid-show, for near-zero cost. **Absence of heartbeat is
the alarm; do not stream telemetry.** Everything else is pull-on-demand:
`/os/ping <token>` → **unicast** `/os/pong <token> <uid>` (replaces `/echo`),
`/os/report` → unicast reply. Streaming rssi/temp/xruns from 100 nodes is just
another broadcast storm; refuse it.

### Transport ruling (seat E)

- **Broadcast** only for low-rate, idempotent, genuinely one-to-many, loss-
  tolerant messages: `/os/hello`, `/os/assign`, fleet `/all/*` admin, the synced
  `/cue <sharedTime>` fire (one tiny message, everyone acts — the correct use of
  broadcast), and the spatial **`/point <x> <y> <r>`** field.
- **Unicast** for targeted or high-rate traffic and all replies: per-device
  parameter sets, `/os/pong`, `/os/report`, fetch progress. Unicast gets WiFi
  MAC-layer ACK+retransmit and does not wake all 100 CPUs. Reply to the
  requester's source IP:up-port (learn the dashboard IP from inbound commands).

**Spatial at scale is broadcast `/point`, not per-device gain.** Dashboard-
computed per-device gain (§6-A) is N×30 Hz = 3000 msgs/s of broadcast at 100
nodes, each parsed-then-discarded by 99 nodes on a single-threaded Pd on a Zero
2 W. Pi-computed (§6-B) is *one* 30 Hz broadcast of a 3-float idempotent
message; each node computes its own falloff. A is fine ≤12 nodes and for the
one-host audition rig; **B is mandatory at fleet scale** and `/point` must be
first-class now.

Port layout that follows: **keep the two LAN sockets** — an up-port (fleet→dash,
today 5550) and an in-port (dash→fleet, today 6660). Two directions on two
sockets is correct; it's also what lets the audition rig share the up-port via
`SO_REUSEADDR`. Do **not** renumber them — migration cost for deployed fleets
buys nothing. The four localhost ports never touch the network; document and
namespace them, optionally fold helper+io behind one Python process later, but
that's cosmetic. The one real change: helper.py now sends the heartbeat to the
up-port itself instead of routing through Pd's `netsend`.

### Capability broadcast (seat G) — verdict: **reject the subsystem, accept a
flat `caps` field.**

A typed capability *registry* is exactly the speculative machinery the values
forbid. But heterogeneity (C) is real and needs *something*: a compact keyword
list carried in `/os/hello` (and re-sent on request), e.g.
`caps = i2c,accel,screen,ch2`. The framework interprets only `engine` and `i2c`
for its own routing; the dashboard and patches read the rest. Concrete uses that
earn it:

1. **Hide I2C controls on non-I2C nodes** (the x86 office box has no bus) —
   otherwise the install screen is full of dead buttons or loud errors.
2. **Engine compatibility** — don't let a Pd patch be pushed to an SC-only node.
3. **Screen / channel count** — the video-mask and spatial features need to know
   which nodes can render.
4. **Asset presence** — a node advertises which asset-sets it holds, which drives
   distribution (below). This is the substitute Bob asked for: metadata at join,
   not a broadcast stream.

### Distribution (seat H)

Kill gdown-on-the-critical-path. 100 nodes fetching from Google Drive means
cloud throttling and a hard internet dependency in an air-gapped venue.

**Dashboard serves an HTTP file store + a manifest (asset-set → files + hashes).
Nodes pull by manifest, verify by hash, resume on drop.** Media-agnostic: it
moves opaque *asset-sets* (folders), not "samples." Contract:
`/os/fetch <asset-set> <manifest-url>` → node diffs against what it has (ties to
`caps` asset-presence), pulls only missing/changed files with HTTP Range so a
WiFi drop mid-download resumes instead of restarting → `/os/fetched
<asset-set> <ok|err>`. Pull (not push) needs no per-node ssh keys and works for
stateless boxes. gdown survives only as an optional *ingest source the dashboard
pulls once*.

**Landing location** (the decision Bob flagged): land assets in a **framework-
owned, engine-neutral dir outside the patch git tree** —
`~/bopOS/assets/<asset-set>/` — and hand patches its root via a startup message
(`ASSETS`, alongside the existing `ACTIVEPATCH`/`RANDOM` sends). Pd, SC, and OF
patches all read the same root. Today's `patches/<active>/bop/samplepacks`
couples big binaries to a patch's git repo and is bop-specific; symlink the old
path to the new dir for one release to keep deployed patches working.

## 4. How it fits the existing system

- **Changes:** heartbeat gains `uid`/`engine-alive` (extends the already-settled
  Python heartbeat); new `/os/hello`↔`/os/assign` round-trip; dashboard grows a
  persistent `uid→assignment` table (seeded from `bopos.devices`); replies go
  unicast; distribution moves to LAN HTTP+manifest with a neutral assets dir;
  `/point` reserved first-class.
- **Stays:** two LAN ports and their numbers; broadcast for `/all/*` admin and
  `/cue`; `bopos.devices` as seed/fallback; `id = -1` unassigned convention; the
  route-by-id Pd logic.
- **Migration:** `uid == MAC` on existing Pis, so deployed fleets keep working
  with zero renumbering; old samplepacks path symlinked one release; `/helper`
  alias already planned. Test entirely in `simfleet` — no hardware needed.

## 5. Why it's right — failure scenarios it survives

1. **DHCP churn / reconnect with new IP** → IP-keyed dashboards lose or
   double-count nodes. Here `uid` in the heartbeat is the join key; IP is only a
   return path. Survives.
2. **Can't pre-register office MACs / MAC randomization** → CSV lookup returns
   "not found," node stuck at `-1`. Here the dashboard-authoritative table +
   operator-assign flow needs no pre-registration. Survives.
3. **Stateless live-image reboots mid-show** → loses id/position. Here the
   dashboard re-pushes the idempotent `/os/assign` on re-hello; the box persists
   nothing. Survives.
4. **30 Hz spatial × 100 nodes over WiFi** → broadcast at basic rate saturates
   airtime, frames drop, audio glitches. Here spatial is one tiny idempotent
   `/point` broadcast; per-device data is unicast. Survives.
5. **Air-gapped venue / Google throttling** → gdown fails on all 100 nodes. Here
   LAN HTTP pull with hash+resume. Survives.

These all trace to the values: performance stability (broadcast discipline,
engine-alive flag), smallest vocabulary (reject the capability registry), fail
loud (`-1` unassigned, `/os/fetched err`, heartbeat-absence-is-the-alarm).

## 6. Tradeoffs, risks, not solving

- **Not solving routed/multi-subnet discovery.** `/os/hello` is link-local; it
  won't cross VLANs. Recommend a flat L2 segment (ideally a wired VLAN or an AP
  *without* client isolation) for performance nights. If subnets are
  unavoidable, the dashboard IP must be configured and hello won't reach — say so
  loudly, don't paper over it.
- **AP client-isolation / broadcast storm-control** can still block the discovery
  broadcast. The unicast return path limits the blast radius once nodes are
  known, but discovery itself depends on L2 broadcast working. This is a venue
  requirement, not something the protocol can fix — name it in the runbook.
- **Ephemeral uid degradation:** MAC randomized + no machine-id + no DMI → uid
  isn't stable across reboot, so the operator re-assigns each boot. Acceptable
  for an attended install; flagged, not hidden.
- **Security:** the broadcast control plane is unauthenticated — anyone on the
  LAN can reboot the fleet. Fine for a closed art LAN, genuinely risky on a
  shared office network. Out of scope here, but Bob should know before the
  office-takeover demo.
- **Not building:** typed capability registry, streamed telemetry, push-based
  distribution, port renumbering.

## 7. Smallest first step

Extend the already-planned Python heartbeat to `/hb <uid> <id> <version>
<engine-alive> [rssi]` and implement the `/os/hello`→`/os/assign` round-trip in
helper.py plus a dashboard-side persistent `uid→assignment` table — exercised end
to end in `simfleet` (N fake nodes, reboot one, watch it re-hello and get its id
back with nothing persisted on the node). This is the load-bearing change;
unicast replies, `/point`, and manifest distribution all layer on after. It needs
no hardware and no renumbering — pure protocol + simulator, exactly what the repo
is set up to test.
