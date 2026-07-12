# bopOS OSC Contract

Version 1.2 — ratified 2026-07-07; amended 2026-07-11 by the patch-seam ruling
(seam council 2026-07-10 + Bob's ratification; record in
`.loom/tied/seam-0-council/` and lore `2026-07-10-patch-seam-council`); amended
2026-07-12 by Bob's removal of the param `role` concept (§8; record in
`.loom/tied/dashboard-7-remove-param-roles/`); revised to v1.2 2026-07-12 by
the engine-boundary ratification (record in
`.loom/tied/engine-boundary-ratification/`): `bopos.py` is each node's sole
LAN citizen, every engine — Pure Data included — consumes one
selector-stripped localhost surface, and v1.1's statement that PD retains a
direct 6660 path is **superseded** (§4).
Provenance of v1.0: five-expert council + judgment + Bob's ratification,
recorded in `.lore/` (`osc-schema-council`). This document is the durable spec;
the council records hold the reasoning and the rejected alternatives.

## 1. Purpose and scope

bopOS moves control and identity between a controller (dashboard) and a fleet of
autonomous nodes. It guarantees each node can say **who it is, whether it's alive,
what it can do, and that it has converged to the intended revision** — always as
*declared facts*, never as hardware or disk assumptions.

The framework owns: identity/liveness, the OSC transport and namespace,
convergence (update/checkout/fetch), the offboard peripheral-bus IO layer, the
sync/cue plane, and the machinery that produces provided terms (clock offset
estimation, point-proximity math). Everything that comes out of the speakers,
LEDs, printer, or monitor is the **patch's**; engine launch is
**patch-declared**; media IO (MIDI/HID/audio-in) is the **engine's**;
control-plane state, point geometry and authoring, and scene authoring are the
**dashboard's**.

**The seam law (ratified 2026-07-10):** bopOS **provides** named, full-state
*terms* the patch subscribes to and enacts; bopOS **owns** the machinery that
produces them; bopOS **enforces** exactly one output control — mute. **bopOS
never composes a provided term into a patch parameter.** A patch that doesn't
consume a term simply isn't controllable by it — unconsumed is a legal no-op,
never an error.

**Scope note:** this contract governs what bopOS *nodes* speak. The dashboard's
sequenced scenes may emit arbitrary OSC to arbitrary hosts — non-bopOS devices are
integrable in a dash-driven install — and the scene language is not constrained to
this vocabulary.

**Governing rule:** every framework capability query has a legal empty answer; a
node never crashes or falls silent for lacking hardware. No WiFi → `rssi` absent.
No I2C → `/io/scan` returns empty and `/io/create` fails loud with
`/io/error <name> no-bus`. No registration → unassigned-and-announcing, never
silence.

## 2. The node contract (declared facts)

A node MUST be able to provide, and the framework MAY assume ONLY, these declared
facts (self-reported, never inferred from hardware):

| Fact | Meaning | Pi default | Live-image default |
|---|---|---|---|
| `uid` | stable opaque correlation key | primary-interface MAC | machine-id / MAC / per-boot UUID |
| `engine` + `entrypoint` | how the engine starts (patch manifest) | `pd … main.pd` | `scsynth`, oF app, … |
| `audio_out` | audio device, or `none` | `DigiAMP` | `default` |
| `io_buses` | offboard buses present | `[i2c]` | `[]` |
| `has_wifi` / `rssi` | link metric available? | yes | absent |
| `update_model` | provisioning model | `persistent` | `ephemeral` |

The contract MUST NOT assume: a WiFi interface or any specific interface name; an
I2C bus; reachable internet; a writable git checkout; a user named `pi`; Pure Data;
or a pre-registered MAC.

## 3. Address grammar

One rule for every LAN message:

```
/<selector>/<plane>/<member>  args…    controller → fleet    selector: all | <id>
/<plane>/<member>             args…    node → controller     (source identifies sender)
```

`bopos.py` routes on the selector (`all` = everyone; id −1 = unassigned) and
strips it before anything reaches an engine — engines never see selectors or
identity routing (v1.2; the old in-patch `route-by-id` is retired). Replies
carry the request's address, so a stray packet in a log is self-describing.

### Planes

| plane | owner | contents |
|---|---|---|
| `/os/*` | framework | identity, liveness, admin, discovery, persistence, distribution (absorbs `/helper/*` and `/system/*`) |
| `/io/*` | framework | offboard bus peripherals (I2C today; verbs are bus-agnostic) |
| `/sync/*` | framework (Python) | forward clock sync — shape pinned in §3.1 (clock-sync thread) |
| `/cue` | framework (Python) | discrete scheduled fires; engines only ever see relative ms (§3.1) |
| `/pt` (canonical `/point`) | framework/dashboard | point geometry broadcast — moving sound sources, arbitrary count; each device decomposes locally (§4.1) |
| `/p/*` | **patch** | patch-declared parameters — the only place output semantics live |

The framework planes are a **closed set**; `/p/*` is open and entirely
patch-owned. `gain` `gain2` `backing` `echo` are patch parameters and live under
`/p/*` (no bare aliases — patches rewrite in lockstep, §13).

### Shorthand addresses

High OSC volume is expected; addresses stay readable but the contract registers
**permanent shorthands** for high-rate messages — canonical and short form both
always valid:

| canonical | shorthand | rationale |
|---|---|---|
| `/point` | `/pt` | up to ~30 Hz broadcast at fleet scale |
| `/os/hb` | `/hb` | the fleet's most frequent framework message |

Shorthands are minted **only** where measured traffic justifies them (this table is
the registry; additions require a contract revision). Patch parameter names under
`/p/*` are the patch's own to keep short.

### 3.1 Sync and cue plane (clock-sync)

Forward clock sync so cues fire sample-tight(ish) over WiFi, engine-agnostically.
The mechanism (HB-style) and design reasoning live in the `clock-sync` thread;
this is the pinned wire shape (additive to the reserved `/sync/*` and `/cue`).

| address | direction | transport | args |
|---|---|---|---|
| `/sync/ping` | leader → fleet | broadcast, 6660 | `<seq:int32> <leaderTimeNs:string>` |
| `/sync/pong` | node → leader | unicast, 5550 | `<seq:int32> <leaderTimeNs:string> <uid:string> <deviceTimeNs:string>` |
| `/<id>/sync/offset` | leader → node | unicast | `<offsetNs:string>` |
| `/cue` | leader → fleet | broadcast, 6660 | `<cueId:string> <sharedTimeNs:string>` |

- **The dashboard backend is the clock leader** (resolved 2026-07-05). It
  broadcasts `/sync/ping` every ~500±100 ms (jittered to avoid lockstep
  bursts). bopos.py answers `/sync/pong` unicast, **echoing** `seq` and
  `leaderTimeNs` so the leader stays stateless and a lone packet is
  self-describing. `deviceTimeNs` is the node's `time.monotonic_ns()` at reply.
- **The leader computes the offset, the node applies it.** Only the leader sees
  the round trip, so it owns `oneWay = RTT/2`,
  `offset = (deviceTime + oneWay) − leaderNow` and its smoothing. It pushes the
  current best estimate per device as `/<id>/sync/offset`. `offset ≡
  deviceClock − leaderClock`.
- **`/<id>/sync/offset` is full-state and idempotent** (§4 law): an absolute
  value, never a delta. The node **slews** its working offset toward it while
  audio runs (never steps); slew is node-internal, not wire state.
- **`/cue` carries one leader-clock instant for the whole fleet.** Each node
  converts locally, `deadlineNs = sharedTimeNs + offsetNs`, waits on its own
  `monotonic_ns()`, then fires the bare `/cue <cueId>` to its engine on
  localhost. The engine never sees absolute time (§12).
- **Encoding:** every time-valued arg is the decimal string of an integer
  nanosecond count from `time.monotonic_ns()` — never a single 32-bit OSC float
  (§12), exact across the two Python endpoints, human-readable in a log, and
  full-resolution. `seq` is a plain int32; `cueId` is a string label (named cues
  allowed). Monotonic, not wall clock: NTP steps must never glitch a cue.
- **Grammar:** `/sync/ping` and `/cue` are the two framework addresses that omit
  the selector — broadcast-only and always fleet-wide. `/sync/pong` is a 2-part
  node→controller reply like `/hb`; `/<id>/sync/offset` is the normal 3-part
  `/<selector>/<plane>/<member>` (selector always a concrete `<id>`).

## 4. Ports and transport

The six ports stay exactly as deployed. The two LAN ports are the public
contract; the four localhost ports are one device's internal plumbing. As of
v1.2 **`bopos.py` is the node's only LAN citizen**: it alone binds 6660 and
sends on 5550. Engines — PD included — live entirely on the localhost ports.
(Supersedes v1.1 §4/§4.1, which kept PD's direct 6660 path; that path was
retained only as a migration safety net and was removed after the relay,
helper-death, and production-macOS N=1 gates passed, 2026-07-12.)

| Port | Listener | Sender | Scope |
|---|---|---|---|
| 5550 | dashboard | bopos.py | LAN broadcast, fleet → dash |
| 6660 | bopos.py (sole binder) | dashboard | LAN broadcast, dash → fleet |
| 6661 | engine (`[bopos]` in PD, OSCdefs in SC, …) | bopos.py | localhost: the selector-stripped engine surface (§4.2) |
| 6662 | engine | io/main.py | localhost: peripheral streams |
| 7770 | bopos.py | engine | localhost: engine requests only (§4.2) |
| 8880 | io/main.py | engine | localhost: I/O commands |

Production engines listen on 6661; an audition instance is assigned its own
port via `BOPOS_ENGINE_PORT`, feeding exactly the same selector-free surface —
the topology is identical, only the port number moves.

**Transport discipline:**

- **Broadcast** only for low-rate, idempotent, genuinely one-to-many messages:
  `/hb`, `/os/assign`, `/all/*` admin, `/cue`, `/pt`, `/os/mute`, `/os/master`.
- **Unicast to the requester** for all request/reply traffic: `/os/pong`,
  `/os/report`, `/os/params`, `/os/rev`, `/os/fetched`. (WiFi broadcast has no
  MAC-layer ACK and rides the lowest basic rate — it is scarce and lossy; replies
  don't wake 100 CPUs.)
- **Control-plane law: every fleet command is full-state and idempotent.** No
  increments. Re-sending anything is always safe — which is also what makes
  spamming `/os/mute` a valid safety procedure.
- The heartbeat is sent by **bopos.py directly to 5550** (engines never touch
  the LAN), so engine death ≠ device death.
- Spatial is the broadcast `/pt` with **node-side decomposition, at every
  scale** — never per-device gain streams. (The dashboard-computed `/p/gain`
  model was built and reverted 2026-07-10: it is O(N) streams on a lossy
  broadcast channel, and it composed a product into a patch parameter,
  violating the §1 seam law. See lore `2026-07-10-patch-seam-council`.)

### 4.1 Provided terms

The registry of values bopOS provides for patches to enact. Like the shorthand
registry (§3), it grows **only by contract revision.** Terms are full-state,
idempotent, and optional to consume; the starter-kit abstractions (PD and SC
both first-class) are the reference consumers.

| term | wire | delivery to the engine | patch obligation (if consumed) |
|---|---|---|---|
| **master** | `/all/os/master <0..1>` — broadcast on change, 6660; also sent in the per-device catch-up push | bopos.py relays selector-stripped `/os/master` to every engine on its engine port | multiply into the final output stage (the `bopos.out~` twin), upstream of nothing — it is the last gain before mute |
| **point** | `/pt <n> <id x y r f>×n` — one frame, all points, atomic; ~20–30 Hz while moving; **silence = hold**; sparse per-point form `/pt <id> <x> <y> <r> <f>` and `/pt/clear <id>` for authoring edits; `f` is a falloff enum (0 linear, 1 smooth, 2 gauss) | bopos.py computes proximity 0→1 per point **per element position** and sends `/pt <pointId> <element> <v>` flat-args on the engine port | map wherever it likes (gain, cutoff, …), upstream of its own volume |

- The **catch-up rule**: a device (re)appearing gets the current `/pt` frame
  and master unicast (piggybacked on the params catch-up) — silence = hold
  only holds for devices that were present.
- Point values are **shaped scalars**, not geometry (raw distance may be added
  later as an option, by revision).
- bopos.py relays matched patch-plane values as `/p/<name> <values…>` on the
  engine port — for every engine (v1.2; PD's direct 6660 path is removed).
  This is transport/selector plumbing only: bopos.py never interprets or
  composes the patch value.
- `/cue` (§3.1) is a provided term avant la lettre: bopos.py owns the clock
  math, the engine receives the bare relative fire.

### 4.2 The engine surface

The whole engine-facing contract, both directions (ratified 2026-07-12).
Engine-received, on the assigned engine port (default 6661), always
selector-stripped:

```
/id <n>                        resolved identity (pushed on assignment and
                               after a /config request)
/os/master <0..1>              the master term (§4.1)
/p/<name> <values…>            patch-declared parameters (§8)
/pt <point> <element> <value>  shaped point scalars (§4.1)
/cue <id>                      scheduled relative fire (§3.1)
/notify <event>                framework notifications (identify, update, …)
```

Engine-sent, localhost 7770, **requests only** — administrative commands
never cross from an engine to the framework:

```
/config                        ask for identity; retry until /id arrives
/store <key> <values…>         persistence store (§10)
/load <key>                    → /load <key> <values…> back on the engine port
/report <name> <values…>       retained typed values for demand inspection (§6)
```

In PD this surface is owned by the `[bopos]` abstraction (`pd/bopos.pd`),
which exposes the buses `bopos-context`, `bopos-master`, `bopos-param`,
`bopos-point`, `bopos-cue`, `bopos-notify`, `bopos-io` and consumes
`to-bopos-io`, `to-bopos-report`. Other engines speak the wire directly
(`templates/supercollider-bopos` is the reference).

**Run context** is generated by a bopOS-owned step and delivered atomically
at launch — never over OSC at boot: PD receives `bopos-context`
`seed <int ≤6 digits>` / `run-id <string>` / `patch <name>` /
`assets <path>` via `-send`; other engines receive `BOPOS_SEED`,
`BOPOS_RUN_ID`, `BOPOS_ACTIVEPATCH`, `BOPOS_ASSETS`, `BOPOS_ENGINE_PORT` in
the environment. The run id is opaque; engines must not parse civil time out
of it. Standalone launch degrades to a useful self-generated context.

**Civil time (amended 2026-07-12):** absolute wall-clock timestamps must not
be sent as OSC floats or used by engines for synchronized cue timing; bopOS
MAY provide civil date/time to an engine, safely encoded, for patch-level
calendar behaviour. The request/event interface for that is deliberately
deferred and unratified.

## 5. Identity, assignment, persistence

- **`uid`** — an opaque stable string the node chooses: persisted machine token →
  primary-interface MAC (discovered, not `wlan0`-hardcoded) → per-boot UUID. On
  deployed Pis `uid == MAC`. IP is a return path, never identity.
- **Assignment** (`id`, `name`, positions) is set from the dashboard:

  ```
  /all/os/assign <uid> <id> <name> [x y]×N
  ```

  Idempotent full-state; **element positions** ride in it, one `x y` pair per
  element, element index = pair order, **0-based** (indices default to
  0-indexing project-wide — Bob, 2026-07-11; no separate verb; the old
  `posx posy pos2x pos2y` spelling is retired — it was two unlabelled
  elements). **device** = the computer (one uid, one heartbeat, one engine
  instance); **element** = a positioned output the patch drives. A patch
  renders N elements by cloning internally (PD `[clone]`, SC synth instances)
  and mapping each element to its output channel; bopos.py computes per-element
  point proximity from this list. Usually N is 1 or 2, but a many-output
  computer IDs as many elements as it drives. The matching node applies it,
  sets its hostname, tells the engine its id, and acks by heartbeating with
  the new id.
- **Persistence is required on persistent hosts.** The node stores its assignment
  via the framework persistence store, so a fleet configured over the network runs
  **standalone** after the network is taken down — dashboard-less, network-less
  operation is a first-class mode (active installations work this way today).
  The dashboard also keeps a persistent `uid → assignment` table for re-setup UX.
  Ephemeral (live-image) hosts sacrifice persistence and are re-assigned each
  boot — an accepted adaptation, not the design center.
- **Boot resolution order:** local persisted assignment → `bopos.devices` seed →
  unassigned. `bopos.devices` is an optional convenience seed, **never a gate**:
  an unknown node takes `id = -1` and announces itself; it must never fall silent.
- **Discovery is the heartbeat.** Unassigned nodes heartbeat fast (~2 s) until
  assigned, then drop to 10 s. There is no separate hello/announce family;
  `/aloha`'s announce role is absorbed (an announce request just triggers an
  immediate heartbeat), and its locate role moves to `/os/identify`.

## 6. Liveness, discovery, debug

```
/hb <uid> <id> <version> <engine-alive 0|1> [rssi]     node → dash, 10 s (2 s unassigned)
/all/os/ping <token>        →  /os/pong <token> <uid>          (unicast; replaces /echo)
/<id>/os/report             →  /os/report <json>               (unicast)
/<id>/os/identify           →  the box chirps/flashes          (locate on install day)
/<id>/os/probe <what>       →  /os/probe <id> <what> <values…> (unicast, one-shot)
/all/os/mute <0|1>                                             (safety)
```

- **`/os/probe` is demand-driven, one-shot inspection** (added by the v1.2
  engine-boundary ratification). It answers from values bopos.py already
  holds: patch-authored values retained from engine `/report <name>
  <values…>` requests, plus the small held fact set (`id`, `uid`, `version`,
  `update_model`). An unknown `what` is silently unanswered. There is **no
  streamed telemetry and no framework meter plane** — `meter_loop`,
  `METERS`/`METER_INTERVAL` config, the broadcast `/rpt` echo chain, and
  manifest `role: "meter"` were all deleted, not renamed. A *leased* probe
  (`… <hz> <ttl>`) was proposed and is deliberately **not** part of v1.2;
  the council text is reference material only.

- Strings come from Python, so no 32-bit float limits apply to `uid`/`version`.
- `engine-alive` distinguishes "box up, engine crashed" from "box gone" — the two
  mid-show failures an artist must tell apart. **Absence of heartbeat is the
  alarm**; there is no streamed telemetry.
- `/os/report` returns the static facts as JSON: engine, has_i2c, has_wifi,
  audio_channels, screen, active patch, uptime, git-rev, update_model,
  contract-version. This is the capability story: **pull, not broadcast.**
- **`/os/mute` is safety-critical.** It is the one framework-owned output control:
  a transport-level kill enforced below patch logic (amixer on Pi; degrades to
  engine-stop where no mixer exists). Broadcast, idempotent, spam-safe — repeated
  sends must always converge on silence. Honest boundary: mute is independent
  of the **engine** (amixer acts below patch logic), not of **bopos.py** —
  bopos.py is the actor, and a dead bopos.py also stops heartbeating, so the
  failure is visible, never silent (the supervised helper-death drill on real
  hardware restored control in ≤2.2 s, 2026-07-12; that recovery bound is a
  standing gate on the sole-binder design). Where no mixer control accepts a mute,
  the fallback is engine-stop: silencing but engine-lethal — a degraded mode,
  not the design centre. The mixer path must be verified per audio board on
  real hardware (DigiAMP, Pimoroni Audio SHIM, class-compliant USB — the
  candidate-control list in `set_mute` grows as boards are benched).

## 7. Admin and convergence (`/os/*` verbs)

Lifecycle verbs always mean one thing: `/os/reboot`, `/os/shutdown`,
`/os/restart-engine` (targeted; replaces pkill-everything — `stop.sh`'s
`pkill python` is retired).

Provisioning verbs are **convergence assertions**, not filesystem operations —
WHAT is fixed by the contract, HOW is chosen by the node's `update_model`:

- `/os/update` — persistent: git pull + reboot (today's behaviour). Ephemeral:
  re-fetch the mutable layer and re-exec, or honestly no-op.
- `/os/checkout <branch>`, `/os/patch <name>`, `/os/addpatch <user> <repo>`,
  `/os/pullpatch` — as today, renamed.
- **Every provisioning verb replies** `/os/rev <sha> <model>` (unicast) so the
  dashboard observes convergence, not fire-and-forget.

## 8. Patch manifest and parameters

A patch ships **`bopos.patch.json`** in its repo root:

```json
{ "engine": "pd", "entrypoint": "main.pd",
  "params": [
    {"name":"gain",    "type":"f", "min":0, "max":1, "default":0.75, "group":"mix", "facilitator":true},
    {"name":"backing", "type":"f", "min":0, "max":1, "default":0.8,  "group":"mix"},
    {"name":"echo",    "type":"i", "min":0, "max":1, "default":0,    "group":"fx"} ],
  "caps": ["screen"], "slots": ["samplepacks"] }
```

- The manifest is the single source of truth for *what starts this patch*
  (engine/entrypoint — PD is the reference engine, not the required one) and
  *what can be controlled* (params). It is diffable, git-friendly, and
  agent-writable.
- bopos.py serves it verbatim: `/<id>/os/params` → `/os/params <json>` (unicast).
- The dashboard **renders controls from the declaration** — no more hardcoded
  sliders. Values flow as `/<id>/p/<name> <value>` or `/all/p/<name> <value>`.
- Fail loud: no manifest → legacy three sliders with a visible "undeclared" badge;
  a `/p/*` value hitting an undeclared name gets a badge, not a guess. The
  launcher validates declared params before start so the manifest can't silently
  drift.
- **`role` — removed (Bob, 2026-07-12):** the param `role` concept is gone
  entirely. `role: "meter"` fell with the 2026-07-12 engine-boundary
  ratification; `role: "volume"` (ratified 2026-07-08) is superseded by
  `facilitator` promotion below — there is no anointed volume param and no
  `gain`-name fallback. Gain staging is purely the patch's business; the
  framework only provides the `master` term (§4.1). Per-element volumes are
  just N promoted params. Validation rejects any `role` key, loudly.
- **`facilitator` (optional; additive, ratified 2026-07-10):** a param
  declaration may carry `"facilitator": true` to promote it onto the
  `/facilitator` surface as a control (rendered as a labelled control on the
  device card; values flow as ordinary `/<sel>/p/<name>`; a card with no
  promoted params is status-only). Promotion of **framework
  verbs** is *never* a manifest concern: an install-level allowlist in
  `installation.json` (`"facilitator_commands": […]`, **default empty**)
  opts specific verbs onto the surface, confirm-gated, with destructive
  convergence verbs (update/checkout/reboot/shutdown) at minimum
  hold-to-confirm. The patch promotes its params; the venue promotes its
  verbs.

## 9. Distribution and landing

```
/<id>/os/fetch <source-uri> <slot>    →    /os/fetched <slot> <ok|err>   (unicast)
```

- `source-uri` dispatches on scheme: `http:` (the fleet-scale path — dashboard
  serves LAN HTTP with a manifest of files + hashes; nodes pull by diff with
  Range-resume; works air-gapped), `gdrive:` (legacy ingest), `file:`.
- **Landing convention:** assets land in a framework-owned, engine-neutral root
  **outside the patch git tree** — `~/bopOS/assets/<slot>/` — handed to every
  engine at launch as part of the run context (§4.2: `bopos-context assets`
  for PD, `BOPOS_ASSETS` for other engines). PD, SC, and oF patches all read
  the same predictable root. Legacy `patches/<active>/bop/samplepacks` is
  symlinked for one release.

## 10. Persistence store

```
/<id>/os/store <key> <values…>        /<id>/os/load <key>  →  /os/load <key> <values…>
```

Python persists, engine gets values back on load. This store also holds the node's
assignment (§5). PD-side state that persists today migrates here so persistence is
engine-agnostic.

## 11. IO plane (`/io/*`)

Unchanged verbs, sharpened boundary:

- **Framework owns what is offboard and bus-addressed on the node** — I2C today
  (SPI/GPIO/serial later through the same registry pattern). Engines do this badly
  or not at all; that is the entire justification.
- **Engine owns its native media IO** — audio, MIDI, HID, display. If engine-side
  input must reach the fleet or dashboard, it surfaces as `/p/*`.
- **Inspection is demand-driven** (v1.2; supersedes the 2026-07-08
  `role: "meter"` republish model, which was deleted with the meter plane): a
  patch retains values it wants inspectable via engine-side `/report <name>
  <values…>` (§4.2), and the dashboard pulls them one-shot with `/os/probe`
  (§6). No subscription stream, no periodic republish, no presentation
  metadata; a future reporting UI must design explicit read-only semantics
  from concrete needs.
- No-bus is a declared legal state: `io_buses: []`, `/io/scan` → empty,
  `/io/create` → `/io/error <name> no-bus`. (`sys_i2c` must degrade the way
  `sys_wireless` already does.)

## 12. Hard constraints

- **PD OSC floats are 32-bit** (~6–7 significant figures). Any value needing more
  crosses the wire as a **string** (uids, versions, epoch/shared times). Absolute
  wall-clock timestamps are never sent as OSC floats and never used by engines
  for synchronized cue timing: the synced clock lives in Python; engines only
  ever receive the bare relative fire (`/cue <cueId> <sharedTime-as-string>` is
  converted by bopos.py to a local deadline before the engine sees it). Civil
  date/time MAY reach an engine, safely encoded, for calendar behaviour — the
  interface is deferred (§4.2).
- Pi Zero 2 W is the constrained reference target; PD is single-threaded — no
  per-frame framework traffic on the engine's socket.

## 13. Migration (deployed fleets: Kite Choir, The Plants)

- **Zero port changes. No reflash. No flag day.**
- `uid == MAC` on Pis, so heartbeat correlation carries over.
- Patches are **rewritten in lockstep** with this contract version (ratified
  2026-07-10: patch-facing wire compatibility is a non-goal — no bare
  `/gain`-style aliases, no dashboard-side master composition for legacy
  patches). **Clean break (amended 2026-07-12):** there are no deployed
  dashboards, so no `/helper/*` compatibility alias exists — the dashboard
  speaks `/os/*` directly and obsolete consumers are not preserved
  speculatively. The old 7770 admin forwarding, `/rpt` echo chain,
  `osc-in`/`osc-out`, direct PD LAN binding, and in-patch identity routing
  are removed, not maintained in parallel. Fleet-level guarantees stand:
  `bopos.devices` seed, samplepacks symlink, zero port changes, `uid == MAC`.
- `bopos.devices` keeps working as the seed. A patch without a manifest still gets
  the legacy sliders.

## 14. Rejected by design (do not reintroduce without a contract revision)

Port consolidation and renumbering; a capability broadcast/registry (pull via
`/os/report` + manifest instead); runtime parameter introspection or
params-announce protocols; telemetry/log streaming (heartbeat absence is the
alarm); envelope-carrying cues (crossfades are dashboard param automation);
a separate hello/handshake family (the fast heartbeat is discovery); per-device
spatial gain broadcast at fleet scale; per-host branching in message semantics
(differences are declared facts, never special cases); dashboard-side
composition of provided terms into patch parameters (the spatial-0 /
master-multiply defect — see §1 seam law); a runtime parameter-dump/query verb
(a patch may implement its own dump; a framework `/os/dump` arrives, if ever,
as a deliberate revision when evidence demands); a `/helper/*` compatibility
alias (clean break, 2026-07-12); framework meter streaming and any `role`
manifest key; the leased probe wire shape (reference material only until a
concrete need drives its ratification); engines issuing administrative
commands or binding LAN ports.
