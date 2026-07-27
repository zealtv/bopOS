# bopOS OSC Contract

**Version 1.13** — base ratified 2026-07-07; latest revision 2026-07-24. The
complete amendment record, with provenance for every revision, is in
[§15 Revision history](#15-revision-history).

This document is the **durable, normative spec** for everything bopOS nodes
speak on the wire. Guides paraphrase it; where they disagree, this document
wins. The council records in `.lore/` hold the reasoning and the rejected
alternatives — this document states only the ratified result.

**How to read it:** §1–§3 give the ownership model and the one address
grammar; §4 pins ports, transport rules, and the engine-facing surface;
§5–§7 cover identity, liveness, and administration; §8–§11 cover the patch
manifest, distribution, persistence, and peripherals; §12–§14 hold the hard
constraints, migration guarantees, and the list of designs deliberately
rejected. A gentler, non-normative tour of the same system is
[ARCHITECTURE.md](ARCHITECTURE.md). To construct a specific message by hand
— the complete address, args, port, and reply, for every sender and
receiver — see [OSC-REFERENCE.md](OSC-REFERENCE.md); this document stays
normative where the two disagree.

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
produces them; bopOS **enforces** exactly one output gate — Device enabled
combined with execution MUTE ALL. **bopOS
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

One rule for every LAN message (the open patch plane may continue after
`<member>` with additional manifest-declared path segments):

```
/<selector>/<plane>/<member>[/<segment>...]  args…  controller → fleet
/<plane>/<member>[/<segment>...]             args…  node → controller
                                                    selector: all | <id> | g<group-id>
```

`bopos.py` routes ordinary selector-addressed messages (`all` = everyone;
id −1 = unassigned;
`g<group-id>` = every assigned node whose persisted Seat membership contains
that group) and
strips it before anything reaches an engine — engines never see selectors or
identity routing (v1.2; the old in-patch `route-by-id` is retired). Replies
carry the request's address, so a stray packet in a log is self-describing.

Group selectors are lowercase `g` followed by one canonical non-negative
signed-int32 decimal ID: `g0`, `g1`, and `g2147483647` are valid; `g`, `G1`,
`g01`, `g-1`, `g+1`, and `g2147483648` are invalid. A group selector is legal
wherever a concrete numeric Seat selector is legal. A node assigned ID `-1`
never matches a group. Groups contain Seats, may overlap or be empty, and are
not nested in v1.5.

Assignment is not an ordinary selector-addressed verb: its address is exactly
literal `/all/os/assign`. Numeric and group-selected assignment spellings are
invalid even when the receiving node currently matches that selector. The
literal-all assignment, UID-administration, and membership envelopes are
handled before generalized selector routing.

One v1.5 administrative envelope is the deliberate exception to numeric
selection:

```
/all/os/to <uid:string> <verb:string> [args...]
```

Every node receives it; only the exact opaque uid match dispatches. The uid is
data, never an OSC address component. Dispatch is direct to an exact allowlist.
The full-state one-argument operations are `enabled <0|1>` and
`hostname <lowercase-hostname>`; the zero-arity operations are `identify`,
`report`, `reboot`, `shutdown`, `restart-engine`, `updatebopos`, `unassign`—with
no recursive address construction. Provided
terms, patch parameters, probes, persistence storage, content distribution and
patch switching remain selector-addressed and cannot pass through this envelope.

The membership synchronization envelope is a second literal-`all`, exact-UID
exception:

```
/all/os/groups <uid:string> <group-id:int32>...
/os/groups     <uid:string> <group-id:int32>...
```

The command tail is the node's complete membership replacement; an empty tail
clears it. Every node validates the entire UID-attributable message before
changing state. IDs must be unique non-negative int32 values. The exact target
sorts the set, persists it first, installs it, then replies with the same UID
and sorted complete set. A UID mismatch, invalid or duplicate ID, or persistence
failure changes nothing and emits no success receipt.

### Planes

| plane | owner | contents |
|---|---|---|
| `/os/*` | framework | identity, liveness, admin, discovery, persistence, distribution (absorbs `/helper/*` and `/system/*`) |
| `/io/*` | framework | offboard bus peripherals (I2C today; verbs are bus-agnostic) |
| `/sync/*` | framework (Python) | forward clock sync — shape pinned in §3.1 (clock-sync thread) |
| `/cue` | framework (Python) | discrete scheduled fires; engines only ever see relative ms (§3.1) |
| `/pt` (canonical `/point`) | framework/dashboard | point geometry broadcast — moving sound sources, arbitrary count; each device decomposes locally (§4.1) |
| `/p/*` | **patch** | patch-declared parameters — the only place output semantics live; numeric params also accept the framework-owned automation grammar (§3.2) |

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

### 3.2 Parameter automation grammar (`/p/*` plane)

Ratified 2026-07-19 (v1.8). Numeric patch parameters accept **framework-owned
automation vocabulary** in the argument list. The ownership split is exact:
the framework owns the grammar — parsing, duration units, curves, scheduling,
LFO phase math, and the catch-up "value now" — while **output semantics remain
entirely patch-owned** (§3 planes table unchanged in spirit: what the value
*means* is still the patch's business). The grammar applies only to addresses
whose manifest declaration is a numeric param (`f` or `i`); it never applies
to string declarations (see the deferred kind below).

**Model: one generator slot per numeric `/p/*` address; last message wins.**
Every message on the address replaces its generator — no layering, no
modulation routing. A plain value is the degenerate generator (a constant),
which is also the dashboard take-over gesture: touching an automated control
sends a plain value and thereby replaces the automation.

```
/<sel>/p/<identity> x                      set (constant)
/<sel>/p/<identity> x <dur>                go to x in dur, from current
/<sel>/p/<identity> x y <dur>              go from x to y in dur
/<sel>/p/<identity> a <dur> b <dur> ...    segment list from current: to a in dur,
                                           then b in dur, ... (even count; odd ≥5 = error)
/<sel>/p/<identity> loop <fade-form>       replay the segment list forever, snapping
                                           back to its start (ignored for 1–2 element forms)
/<sel>/p/<identity> stop                   freeze at current output
/<sel>/p/<identity> lfo <shape> <min> <max> <period> [p:<0..1>] [f] [c:<n>]
```

- **Arity shorthand** (kept from bop): the 3-element form is the only one
  with an explicit start value; segment lists always start from current —
  documented asymmetry.
- **Durations**: a bare number is **ms** (legacy); a string with unit suffix
  is `250ms`, `10s`, `1.5m`, `2h`. Musical units (beats/bars) never reach
  the wire — the authoring layer compiles them to ms at send time; tempo and
  transport stay out of the device contract (deferred with
  `scene-sequencing`).
- **Curve**: one optional trailing `c:<n>` token per message — a signed
  exponent; `0`/omitted linear, `> 0` ease-in-ish, `< 0` ease-out-ish. It
  applies to every segment in the message; there are no per-segment curves.
- **Options**: short forms `c:<n>` `p:<0..1>` `f` are **canonical on the
  wire** (the dashboard emits them; OSC strings pad to 4-byte boundaries);
  `curve:` `phase:` `free` are accepted hand-typed aliases. Keywords lead
  (`loop`, `stop`, `lfo`), options trail.
- **LFO**: shapes `sine tri saw square sh drift` (`sh` sample-and-hold
  random, `drift` smoothed random). Period takes the same duration forms as
  fades. Phase is **clock-anchored to the sync plane by default** —
  `((t_synced / period) + phase) mod 1` — which makes an LFO message
  full-state and idempotent: resend is always safe and a late joiner lands
  in phase with the fleet. `f` (free) opts into per-device random phase for
  deliberate decorrelation. `c:` shapes segment interpolation where
  meaningful (tri/saw/drift).
- **Int params**: the generator interpolates continuously; output
  **truncates (floor)** and is emitted **exactly once at each integer
  crossing**, in either direction — no duplicates, no skips at control rate.
- **Catch-up (the full-state law preserved)**: sync LFOs catch up by
  verbatim replay; free LFOs restart phase on resend by design; fades are
  not replay-safe mid-flight, so the catch-up source sends the **computed
  current value** (a constant), and a completed fade's destination is the
  stored full-state value.
- **Decomposition lives in bopos.py, never in engines**: bopOS evaluates every
  generator at a ~30–50 Hz control tick and engines receive only ordinary
  selector-free scalar `/p/*` values. Duration atoms, grammar tokens, 64-bit
  time, and absolute clocks never enter engines (§12); existing scalar patch
  consumers remain unchanged. This is the `/pt` node-side-decomposition precedent, not the
  reverted dashboard-computed `/p/gain` composition (§14).

**Deferred, noted not decided:** string and mixed-array addresses become a
distinct **non-param manifest kind** in a later additive amendment — set-only,
full-state, the grammar keywords never applying. Its name ("atom" was
disliked; candidates: attribute, property) and its plane (`/p/*` vs a
dedicated one such as `/a/*`) are both open. Until that amendment, string
params remain plain set-only values and the automation vocabulary is
reserved: a string-typed declaration whose value collides with a grammar
keyword is the patch author's foot-gun to avoid.

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
  `/hb`, `/os/assign`, `/all/*` admin and membership, `/cue`, `/pt`, `/os/mute`,
  `/os/master`.
- **Unicast to the requester** for all request/reply traffic: `/os/pong`,
  `/os/report`, `/os/groups`, `/os/params`, `/os/patches`, `/os/assets`,
  `/os/rev`, `/os/fetched`, `/os/hostname`, `/os/enabled`. (WiFi
  broadcast has no MAC-layer ACK and rides the lowest basic rate — it is scarce
  and lossy; replies don't wake 100 CPUs.)
- **Control-plane law: every fleet command is full-state and idempotent.** No
  increments. Re-sending anything is always safe — which is also what makes
  repeatedly sending `/all/os/mute 1` a valid safety procedure.
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
| **master** | `/all/os/master <0..1>` — broadcast on change, 6660; also sent in the per-device catch-up push | bopos.py relays selector-stripped `/os/master` to every engine on its engine port | multiply into the final output stage (the `bopos.out~` twin), upstream of nothing — it is the last gain before the framework output gate |
| **point** | `/pt <n> <id x y r f>×n` — one frame, all points, atomic; ~20–30 Hz while moving; **silence = hold**; sparse per-point form `/pt <id> <x> <y> <r> <f>` and `/pt/clear <id>` for authoring edits; `f` is a falloff enum (0 linear, 1 smooth, 2 gauss) | bopos.py computes proximity 0→1 per point **per element position** and sends `/pt <pointId> <element> <v>` flat-args on the engine port | map wherever it likes (gain, cutoff, …), upstream of its own volume |

- The **catch-up rule**: a device (re)appearing gets the current `/pt` frame
  and master unicast (piggybacked on the params catch-up) — silence = hold
  only holds for devices that were present.
- Point values are **shaped scalars**, not geometry (raw distance may be added
  later as an option, by revision).
- bopos.py relays matched patch-plane values as
  `/p/<segment>[/<segment>...] <values…>` on the engine port — for every
  engine (v1.2; PD's direct 6660 path is removed). It removes only the fleet
  selector and preserves every parameter segment and argument.
  This is transport/selector plumbing only: bopos.py never interprets or
  composes the patch value.
- Group matching removes exactly the same one fleet-selector segment as `all`
  and numeric Seat matching. Thus `/g1/p/gain` reaches an engine as `/p/gain`,
  and `/g1/p/track1/fx/distortion` reaches it as
  `/p/track1/fx/distortion`; group identity never reaches the engine.
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
/p/<segment>[/<segment>...] <values…>
                               patch-declared parameters (§8)
/pt <point> <element> <value>  shaped point scalars (§4.1)
/cue <id>                      scheduled relative fire (§3.1)
/notify <event>                framework notifications (identify, update, …)
/groups <int...>               Seat-group membership: sorted ids, or the
                               sentinel -1 alone for no membership (engine
                               group-context amendment, 2026-07-20 — pushed
                               after every durable membership change; see
                               the run-context paragraph in §4 for the
                               launch delivery)
```

Engine-sent, localhost 7770, requests plus a bounded admin exception (Bob,
2026-07-17 — see §15 v1.7): administrative commands otherwise never cross
from an engine to the framework, but a patch running on a Pi may ask for the
same handful of node-lifecycle actions the dashboard can already trigger:

```
/config                        ask for identity; retry until /id arrives
/store <key> <values…>         persistence store (§10)
/load <key>                    → /load <key> <values…> back on the engine port
/report <name> <values…>       retained typed values for demand inspection (§6)
/log <stream> <values…>        append one entry to the named append-only log
                               stream (v1.12, additive). The node stamps it at
                               receipt with local civil time (ISO-8601 with
                               offset, ms precision) and appends one
                               tab-separated line
                               `timestamp<TAB>stream<TAB>values…` (values
                               space-joined) to a per-stream daily file
                               `<stream>-YYYY-MM-DD.log` under the log
                               destination (the internal default `~/bopos-logs/`;
                               the internal/usb selection is a later additive
                               revision). Stream names match the report rule
                               `[A-Za-z0-9_-]+`. No reply;
                               fire-and-forget like `/store`. An invalid or
                               missing stream name is dropped with a logged
                               warning, never fatal. Absolute time never enters
                               PD (§12) — the patch sends events or relative
                               intervals; the node owns the clock.
/admin <action>                bounded admin request (v1.7, additive);
                               action ∈ {update-patch, update-bopos, shutdown,
                               reboot} — routes to the node's existing admin
                               behaviour (the same code paths the dashboard
                               verbs use: pull-active-patch, update, shutdown,
                               reboot in python/bopos.py). No selector, no
                               reply to the engine — these actions are
                               terminal or restart the engine anyway; outcome
                               receipts continue to flow to the LAN model
                               where applicable (§7). Unknown actions are
                               ignored with a logged warning, never fatal.
```

In PD this surface is owned by the `[bopos]` abstraction (`pd/bopos.pd`),
which exposes the buses `bopos-context`, `bopos-master`, `bopos-param`,
`bopos-point`, `bopos-cue`, `bopos-notify`, `bopos-io` and consumes
`to-bopos-io`, `to-bopos-report`. Other engines speak the wire directly
(`patches/demo-sc` is the reference). The PD-side bus plumbing for `/admin`
(e.g. a `to-bopos-admin` bus consumed by `[bopos]`) is not yet wired in
`pd/bopos.pd` — that patch edit is Bob's to add; agents never edit `.pd`
files.

**Run context** is generated by a bopOS-owned step and delivered atomically
at launch — never over OSC at boot: PD receives `bopos-context`
`seed <int ≤6 digits>` / `run-id <string>` / `patch <name>` /
`assets <absolute-path...>` via `-send`; other engines receive `BOPOS_SEED`,
`BOPOS_RUN_ID`, `BOPOS_ACTIVEPATCH`, `BOPOS_ASSETS`, `BOPOS_ENGINE_PORT` in
the environment. `BOPOS_ASSETS` is a UTF-8 JSON array of the same paths in the
same order. The run id is opaque; engines must not parse civil time out of it.
Standalone launch degrades to a useful self-generated context.

**Asset slots (v1.9):** the `assets` value is a launch-time snapshot of every
installed asset slot. Each path names one immediate, visible, non-symlink
directory below the framework-owned assets directory. Paths are ordered by
slot name for deterministic enumeration; order does not define search or
override priority. Zero paths is the empty set (`bopos-context assets` /
`BOPOS_ASSETS=[]`), and one path is a one-element list. The set includes every
installed slot, not only manifest-declared slots, and changes only when the
engine is next started. This intentionally replaces the pre-v1.9 scalar
assets-root meaning.
PD additionally receives `bopos-context version <string>` and
`bopos-context patch-fingerprint <string>` (v1.7, additive); other engines
receive `BOPOS_VERSION` and `BOPOS_PATCH_FINGERPRINT` in the environment.
`version` is the node's git shorthand (what heartbeats already carry);
`patch-fingerprint` is the active patch's canonical content fingerprint (§7,
v1.4 sense), or the literal string `unknown` when it cannot be resolved at
launch. Both are strings end-to-end — never floats (PD's OSC floats are
32-bit; see the house rule in `CLAUDE.md`). Patch name is already delivered
via `bopos-context patch <name>` above; this is additive.

**Seat-group membership (engine group-context amendment, 2026-07-20):** run
context additionally carries the node's current Seat-group membership,
delivered at launch alongside seed/run-id/patch/assets/version/
patch-fingerprint, and re-delivered in full after every successful,
durably-persisted membership change — including the durable clear that
assignment to a different Seat and unassignment both perform (§5). PD
receives `bopos-context groups <int...>` at launch via `-send`, then the
same shape live via `/groups <int...>` on the engine port (§4.2) whenever
membership changes while the engine is running; non-PD engines receive
`BOPOS_GROUPS` (space-separated ints) in the launch environment and the
same `/groups` wire message for live updates, keeping the boundary
equivalent across engines. Group IDs are OSC integers in canonical sorted
order; the single sentinel integer `-1` is the sole wire spelling for no
membership — never an empty argument list. Only successfully applied
durable state reaches the engine: a rejected or failed-to-persist
membership change leaves the engine's last-known groups untouched, and a
Seat's membership never leaks across an assignment/unassignment transition
because the clear is durably committed before the new identity becomes
routable.

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
- **Unassignment (v1.5)** is `/all/os/to <uid> unassign`. It is idempotent:
  the exact target replaces its persisted assignment with an explicit `-1`
  tombstone (so a CSV seed cannot resurrect it), sets framework and engine ID
  to `-1`, retains hostname, clears element positions and emits an immediate
  uid-bearing heartbeat. It clears persisted group membership in the same
  fail-closed transition. A controller uses that heartbeat as the revocation
  confirmation before removing or replacing a live binding.
- **Seat-group membership** is a sorted unique list of group IDs persisted on
  each node under its assigned Seat. Repeating an assignment to the same Seat
  preserves it. Direct assignment to a different Seat durably clears it before
  the new ID becomes routable; synchronization then supplies the new Seat's
  full set. A failed membership write retains the old in-memory and persisted
  set and has no receipt. Dashboard-side membership belongs to Seats, so it
  survives bind, unbind, and physical-device replacement.
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
/all/os/to <uid> enabled <0|1> → /os/enabled <uid> <device-enabled> <output-enabled>
/all/os/to <uid> hostname <name> → /os/hostname <uid> <name> <ok|err>
/all/os/to <uid> audio-config <json>
    → /os/audio-config <uid> <ok|err> <phase> <json>
/all/os/to <uid> log-config <json>
    → /os/log-config <uid> <ok|err> <json>
```

For one physical device, including an unassigned node, v1.5 uses
`/all/os/to <uid> report` and `/all/os/to <uid> identify`. Report retains the
same uid-bearing `/os/report <json>` reply; Identify has no reply. The older
`/all/os/identify <uid>` spelling remains a compatibility alias while callers
move to the uniform envelope.

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
- `/os/report` returns the static facts as JSON: hostname, engine, has_i2c,
  has_wifi, audio_channels, screen, active patch, uptime, git-rev,
  update_model, contract-version, the sorted `groups` array, persistent
  `device_enabled`, execution `mute_all`, effective `output_enabled`, the
  `audio` object below, and the `log` object below. This
  is the capability story: **pull, not broadcast.** The groups fact is reconciliation
  evidence; `/os/groups` is the immediate write receipt.
- **The framework output gate is safety-critical.** It is a transport-level
  kill enforced below patch logic (amixer on Pi; degrades to
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
  The broadcast `/all/os/mute` value is execution MUTE ALL and follows the
  active Live, Simulation, or Patch Edit target like master. The exact-UID
  `/all/os/to <uid> enabled <0|1>` value belongs only to that physical device
  and is persisted before `/os/enabled <uid> <device-enabled>
  <output-enabled>` acknowledges it. `output_enabled` is
  `device_enabled AND NOT mute_all`; the hardware mixer applies its inverse
  before or while the engine launches. Execution-target transitions never
  mutate or replay Device enabled.
- **Exact-device hostname** is a full-state administrative operation, not Seat
  identity. `<name>` is 1–63 lowercase ASCII letters/digits with internal
  hyphens only, beginning and ending alphanumeric. The node changes its OS
  hostname through pre-provisioned non-interactive authorization and returns
  `/os/hostname <uid> <name> ok` only after the privileged helper succeeds;
  unavailable authorization or OS failure returns `err`. Repeating the current
  hostname is an idempotent success. No Seat, alias, element, or engine state is
  changed by this verb.
- **Exact-device audio configuration (v1.11)** is physical administration and
  always follows the installation-LAN route, independent of Live, Simulation,
  or Patch Edit execution. The complete JSON object contains `card`,
  `mixer_control`, `sample_rate`, `period_size`, and `nperiods`. `card` must be
  one of the node's currently detected ALSA playback cards;
  `mixer_control` is a detected simple control or JSON null for Auto; rate is
  one of 22050, 32000, 44100, 48000, 88200, or 96000; period size is one of
  64, 128, 256, 512, 1024, or 2048 frames; and periods is 2 or 3. Missing,
  additional, partial, wrongly typed, unavailable, or out-of-range values
  reject the whole request.
  Applying writes only the node-level `bopos.config`, restarts JACK and the
  patch engine while the framework listener remains alive, and rolls back to
  the prior file and engine configuration if candidate startup fails. Terminal
  receipt phases are `applied`, `invalid`, `rolled-back`, and
  `rollback-failed`; the final JSON argument is the same complete `audio`
  object carried by `/os/report`. After candidate or rollback startup the node
  reapplies `device_enabled AND NOT mute_all` to the active card.
  The `audio` report object contains `configured`, boot-local `active` (or
  null), detected playback `cards` (`id`, index, label, and mixer controls),
  `status`, and `error`. Detection is point-in-time availability, not a
  capability promise or a periodic stream. This routine path never edits boot
  overlays or invokes privileged provisioning.
- **Exact-device log configuration (v1.13)** is physical administration on the
  same installation-LAN route, independent of execution target. The complete
  JSON object is exactly `{"destination": "internal"|"usb"}` — a bounded choice,
  no free paths; missing, additional, wrongly typed, or out-of-range values
  reject the whole request. Applying writes only `LOG_DESTINATION` in the
  node-level `bopos.config`; there is no engine restart (logging is independent
  of audio) and no rollback phase — the write is atomic and the receipt carries
  the resulting state. `internal` is the SD-card default `~/bopos-logs/`; `usb`
  is the auto-mounted stick at `/media/bopos-usb/bopos-logs/`. When `usb` is
  configured but no stick is mounted, entries fall back to `internal` and stay
  on the SD card — never dropped, never RAM-buffered, no copy-on-insert
  catch-up. The effective destination is resolved per entry, so a hot-inserted
  or removed stick takes effect on the next write without a restart. The `log`
  report object carried by `/os/report` (and the receipt JSON) contains
  `destination` (configured), `effective` (what is actually written now), and
  `usb_present` (media presence) — configured vs effective vs media are all
  visible without SSH. Log *content* is not browsable over OSC in v1; retrieval
  is the USB stick or SSH.

## 7. Admin and convergence (`/os/*` verbs)

Lifecycle verbs always mean one thing: `/os/reboot`, `/os/shutdown`,
`/os/restart-engine` (targeted; replaces pkill-everything — `stop.sh`'s
`pkill python` is retired).

Provisioning verbs are **convergence assertions**, not filesystem operations —
WHAT is fixed by the contract, HOW is chosen by the node's `update_model`:

- `/os/updatebopos` updates the bopOS framework only — persistent: git pull +
  reboot (today's behaviour). Ephemeral: re-fetch the mutable layer and re-exec,
  or honestly no-op. The old `/os/update` spelling has no alias.
- `/os/checkout <branch>`, `/os/patch <name>`, `/os/addpatch <user> <repo>`,
  `/os/pullpatch` — as today, renamed.
- `/os/patch <name>` keeps the OS and helper online: stop the current engine
  stack, select the validated installed patch, launch its engine, then send the
  provisioning receipt. It never reboots the device.
- `/<id>/os/patches` → `/os/patches <json>` (unicast) lists installed
  patches as objects `{name, active, git, manifest}`. The three flags are
  booleans; `manifest` means `bopos.patch.json` is present and valid.
  Each entry may also carry `fingerprint` (v1.4, additive): the 64-hex
  sha256 of the canonical directory-manifest JSON — identical to the host
  catalog fingerprint for the same bytes (dot-entries, symlinks, and `.part`
  files excluded from the walk). Absent from pre-v1.4 nodes, and from an
  entry whose content cannot be read; every consumer tolerates absence.
- `/<id>/os/assets` → `/os/assets <json>` (unicast) lists installed asset
  slots as objects `{name, fingerprint, files, bytes}`. `name` is a top-level
  non-dot, non-symlink directory under `~/bopOS/assets/`; `files` and `bytes`
  are fresh counts from the canonical manifest walk, excluding dot entries,
  symlinks, and `.part` files. `fingerprint` is the same canonical
  directory-manifest sha256 used by the host catalog, or JSON `null` while the
  node's nonblocking stat-signature cache is still warming. An empty list means
  no installed slots; no reply means inventory unknown. The query path never
  hashes file contents synchronously.
- `/os/droppatch <name>` removes an inactive patch and refuses the active
  patch. `/os/dropassets <slot>` removes an asset slot.
- **Every provisioning verb replies** `/os/rev <sha> <model> <uid> [<status>
  <phase>]` (unicast; uid additive in v1.5, optional outcome additive in v1.6)
  so the dashboard observes attributable convergence, not fire-and-forget.
  `status` is `ok` or `err`; `phase` is a short machine-readable token such as
  `pull`, `authorization`, `converged`, or `reboot`. An `updatebopos` success
  receipt is sent before requesting reboot; a rejected reboot produces a
  second `err reboot` receipt. This includes both
  drop verbs; `/os/patches` is a query and replies with its listing instead.
- `/os/getsamples` is removed. Assets use `/os/fetch`; there is no alias.

## 8. Patch manifest and parameters

A patch ships **`bopos.patch.json`** in its patch root:

```json
{ "engine": "pd", "entrypoint": "main.pd",
  "params": [
    {"path":["instrument","marimba"], "name":"gain", "type":"f", "min":0, "max":1, "default":0.75, "dashboard":true},
    {"name":"backing", "type":"f", "min":0, "max":1, "default":0.8},
    {"name":"echo",    "type":"i", "min":0, "max":1, "default":0} ],
  "cues": [
    {"id":"snap", "label":"Snap", "description":"Fire the snap gesture"} ],
  "caps": ["screen"], "slots": ["samplepacks"] }
```

- The manifest is the single source of truth for *what starts this patch*
  (engine/entrypoint — PD is the reference engine, not the required one) and
  *what can be controlled* (params). It is diffable, git-friendly, and
  agent-writable.
- A valid manifest is required. Missing or invalid `bopos.patch.json` fails
  launch loudly; there is no undeclared `main.pd` fallback. Patch-level
  `bopos.config` is retired; the framework's node-level root `bopos.config`
  is unrelated and remains valid.
- bopos.py serves it verbatim: `/<id>/os/params` → `/os/params <json>` (unicast).
- `name` is the leaf parameter segment. Optional `path` is an array of parent
  segments; the canonical public identity is their slash-joined sequence plus
  `name` (for example `instrument/marimba/gain`). `name` and every `path`
  entry match `[A-Za-z0-9_-]+` exactly. There is no escaping, normalization,
  dot syntax, or slash syntax inside a segment. A qualified identity is at
  most eight segments and 255 ASCII bytes, and must be unique in its manifest;
  duplicate leaves in distinct paths are legal. The retired presentation-only
  `group` field is ignored when loading old manifests and stripped on save;
  an absent `path` is simply flat.
- An omitted or empty `path` retains byte-for-behavior compatibility: `gain`
  remains `/p/gain`. The dashboard **renders controls from the declaration** —
  no more hardcoded sliders. Nested values flow as
  `/<id>/p/instrument/marimba/gain <value>` or
  `/all/p/instrument/marimba/gain <value>`, and engines receive the identical
  selector-free `/p/instrument/marimba/gain <value>` hierarchy.
- A `/p/*` value hitting an undeclared qualified identity gets a badge, not a
  guess. The
  launcher validates declared params before start so the manifest cannot
  silently drift.
- **`role` — removed (Bob, 2026-07-12):** the param `role` concept is gone
  entirely. `role: "meter"` fell with the 2026-07-12 engine-boundary
  ratification; `role: "volume"` (ratified 2026-07-08) is superseded by
  `dashboard` promotion below — there is no anointed volume param and no
  `gain`-name fallback. Gain staging is purely the patch's business; the
  framework only provides the `master` term (§4.1). Per-element volumes are
  just N promoted params. Validation rejects any `role` key, loudly.
- **`dashboard` (optional; renamed 2026-07-19; semantics narrowed
  2026-07-27):** every param declaration appears on the desktop Control tab
  and Device-tab control panel. A declaration may carry `"dashboard": true`
  to additionally promote it onto the simplified standalone `/facilitator`
  surface (rendered as a labelled control on the device card; values flow as ordinary
  `/<sel>/p/<segment>[/<segment>...]`; a card with no
  promoted params is status-only). Promotion of **framework
  verbs** is *never* a manifest concern: an install-level allowlist in
  `installation.json` (`"facilitator_commands": […]`, **default empty**)
  opts specific verbs onto the surface, confirm-gated, with destructive
  convergence verbs (updatebopos/checkout/reboot/shutdown) at minimum
  hold-to-confirm. The patch promotes its params; the venue promotes its
  verbs. Loaders accept the legacy `facilitator` spelling and normalize it to
  `dashboard`; saves emit only `dashboard`. If both spellings are present with
  conflicting values, the manifest is invalid.
- **`cues` (optional; additive, v1.4):** a list of cue declarations the patch
  responds to: `{"id": <string>, "label": <string, optional>,
  "description": <string, optional>}`. `id` is the exact string delivered as
  the bare relative fire `/cue <id>` (§3.1 unchanged: engines never see
  absolute time). Declarations are documentation and UI surface only — the
  framework neither filters undeclared cue IDs nor schedules anything from
  the manifest. Duplicate IDs are invalid. An absent `cues` key is valid.

## 9. Distribution and landing

```
/<id>/os/fetch <source-uri> <slot>          → /os/fetched <slot> <ok|err>
/<id>/os/fetch <source-uri> patch:<name>    → /os/fetched patch:<name> <ok|err>
```

While a valid request is pending, the node unicasts
`/os/fetch-progress <slot|patch:name> <queued|fetching>` to each requester.
These are honest phase states, not invented percentages; `/os/fetched` remains
the terminal receipt. A coalesced requester receives the phase current when it
joins the job.

- `source-uri` dispatches on scheme: `http:` (the fleet-scale path — dashboard
  serves LAN HTTP with a manifest of files + hashes; nodes pull by diff with
  Range-resume; works air-gapped) or `file:`. The legacy `gdrive:` scheme is
  removed.
- **Asset landing convention:** each top-level asset slot lands in the
  framework-owned, engine-neutral directory **outside the patch git tree** —
  `~/bopOS/assets/<slot>/`. At launch, bopOS hands every installed slot to the
  engine as its absolute folder path through the §4.2 list
  (`bopos-context assets <absolute-path...>` for PD, JSON-array
  `BOPOS_ASSETS` for other engines). Distribution and inventory continue to
  address each slot by its `<slot>` basename. The retired
  `patches/<active>/bop/samplepacks` compatibility symlink is not created;
  every asset consumer uses the run-context slot paths directly.
- **Patch landing convention:** `patch:<name>` lands in
  `~/bopOS/patches/<name>/` with the same diff, resume, hash-verification and
  prune-to-manifest convergence semantics as an asset slot. A device patch is
  either git-managed or host-mirrored: fetch refuses with `err` when the target
  contains `.git`.
- Fetching the active patch is allowed. The node stops its engine, converges
  the patch, restarts the engine, then replies. The dashboard must confirm-gate
  this disruptive operation; the node does not refuse it.

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

- **Zero port changes. No reflash.**
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
  `bopos.devices` seed, zero port changes, `uid == MAC`. The temporary
  `samplepacks` compatibility symlink was retired after the first real-device
  Assets workflow gate. In v1.9, patches consume the run-context list of
  absolute asset-slot paths directly; the former scalar root meaning is not
  retained in parallel.
- **v1.3 hard break:** Kite Choir and The Plants move in lockstep to
  `/os/updatebopos`, manifest-required patch launch, and the distribution
  surface above. There are no `/os/update` or `/os/getsamples` aliases, no
  `gdrive:` fetch scheme, no patch-level `bopos.config`, and no no-manifest
  `main.pd` fallback. The sibling `kite-choir-brains/.loom`
  `bopos-uptodate` work coordinates that fleet migration; it is not duplicated
  in this repository.
- `bopos.devices` keeps working as the seed.

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
The `gdrive:` fetch scheme, `/os/getsamples`, undeclared-patch launch, and
patch-level `bopos.config` are likewise rejected; media acquisition on the
conducting computer is outside the node contract, and host-to-node transfer
uses the asset/patch mirror in §9.

## 15. Revision history

Every revision below was ratified by Bob; the cited records hold the full
reasoning.

| version | date | change | record |
|---|---|---|---|
| 1.0 | 2026-07-07 | Base contract ratified: five-expert council + judgment + Bob's ratification. | `.lore/` `osc-schema-council` |
| 1.0 am. | 2026-07-11 | Patch-seam ruling (seam council 2026-07-10 + ratification). | `.loom/tied/seam-0-council/`; lore `2026-07-10-patch-seam-council` |
| 1.0 am. | 2026-07-12 | Param `role` concept removed entirely (§8). | `.loom/tied/dashboard-7-remove-param-roles/` |
| 1.2 | 2026-07-12 | Engine-boundary ratification: `bopos.py` is each node's sole LAN citizen; every engine — Pure Data included — consumes one selector-stripped localhost surface; v1.1's direct PD 6660 path is **superseded** (§4). | `.loom/tied/engine-boundary-ratification/` |
| 1.3 | 2026-07-13 | Patch-distribution ratification: host-mirrored patches share the fetch convergence path with assets; manifests mandatory; legacy `gdrive:`/`getsamples` removed; `/os/update` renamed `/os/updatebopos`. Deployed fleets adopt these hard breaks in lockstep. | `.loom/tied/dist-0-proposal/` |
| 1.4 | 2026-07-14 | Fleet-patch fingerprint amendment: `/os/patches` entries may carry a content `fingerprint` (§7, additive). Patch-editor cues amendment: patches may document handled cue IDs (§8, additive). Folded into one revision (Bob, Q4 "fold in"). | `.loom/tied/fp-0-design-proposal/`; `.lore/items/2026-07-14-patch-editor-design-ratified/` |
| 1.5 | 2026-07-15 | Seat/Device boundary ratification: allowlisted exact-UID administration envelope; node unassignment and uid-attributable revision receipts make binding revocation safe. | `.loom/tied/06-seat-device-boundary-design/` |
| 1.5 am. | 2026-07-16 | Exact physical-device mute: the exact-UID envelope carries persistent box mute intent and reports both that layer and its effective OR with the session fleet-safety overlay. | `.loom/tied/12-dashboard-live-controls/device-mute-contract-proposal.md` |
| 1.5 am. | 2026-07-16 | Alias-derived hostname action: the exact-UID envelope can apply one validated full-state hostname with an attributable terminal receipt. | `.loom/tied/19-alias-hostname-action/` |
| 1.5 am. | 2026-07-16 | Nested parameter addresses: declarations may carry a structural `path`; the complete variable-length hierarchy survives selector removal unchanged. Additive; flat declarations and wire addresses unchanged. | `.loom/tied/param-address-0-design/` |
| 1.5 am. | 2026-07-16 | Seat groups: canonical `g<id>` selectors route from node-local persisted Seat membership, synchronized by an attributable additive full-state envelope. | `.loom/tied/seat-groups-0-design/` |
| 1.6 | 2026-07-16 | Asset-inventory amendment (design 2026-07-15): nodes expose durable observed asset-slot facts, including canonical fingerprints once the nonblocking cache resolves. Also carries the additive unattended-update outcome receipts (§7). | `.lore/items/2026-07-15-asset-management-direction/`; stitch `11a-device-asset-inventory` |
| 1.7 | 2026-07-17 | Patch-admin-surface amendment (Bob, 2026-07-17): bounded engine-sent `/admin <action>` request (§4.2) softens the "administrative commands never cross" rule for `update-patch`, `update-bopos`, `shutdown`, `reboot`; run context additively carries `version` and `patch-fingerprint` to the engine (§4.2). | `.loom/tied/1-contract-amendment/` |
| 1.8 | 2026-07-19 | Parameter-automation grammar (§3.2): generator-slot model on numeric `/p/*` params — constants, string-unit timed fades, `loop`, `stop`, clock-anchored idempotent LFOs, `c:`/`p:`/`f` option shorthand, floor-and-emit-per-crossing ints, fades catching up as computed constants. Decomposition in bopos.py; Bob's 2026-07-20 audible ruling clarifies that engines receive scalar control ticks only, so existing patches remain unchanged. String/mixed-array kind explicitly deferred (name and plane open). | `.lore/items/2026-07-19-param-automation-design-ratified/`; stitches `automation-0-design-ratification`, `aa-2a-scalar-engine-frames` |
| 1.8 am. | 2026-07-19 | Patch-manifest presentation tidy (§8): promotion key renamed `facilitator` → `dashboard` with compatible normalization and conflicting dual-key rejection; retired `group` is ignored on load and stripped on save. | stitch `p7-patch-tab-tidy` |
| 1.8 am. | 2026-07-20 | Engine group-context amendment (§4, §4.2): the node's current Seat-group membership joins run context, delivered at launch and re-delivered after every successful, durably-persisted membership change (including assignment/unassignment clears). Wire shape is sorted OSC ints or the single sentinel `-1`; PD's `bopos-context groups <int...>` bus and the new `/groups <int...>` engine-received term keep non-PD engines boundary-equivalent via `BOPOS_GROUPS` and the same live `/groups` message. Purely additive — no existing term changes shape. | stitch `engine-group-context` |
| 1.9 | 2026-07-23 | Multi-asset-slot run-context revision (§4.2, §9): the engine receives the deterministic list of absolute installed-slot folder paths instead of one assets root. PD gets `bopos-context assets <absolute-path...>`; other engines get the same list as JSON-array `BOPOS_ASSETS`. Intentional scalar-root-to-list migration. | stitch `1-context-list-design` |
| 1.10 | 2026-07-23 | Physical/execution routing revision: exact-device `mute` becomes positive `enabled`, reports `device_enabled`, `mute_all`, and `output_enabled`, and execution transitions cannot replay physical-device state. MUTE ALL remains execution-scoped like master. | thread `37-physical-device-control-routing` |
| 1.11 | 2026-07-23 | Exact physical-device audio configuration: detected ALSA cards only, complete validated JACK settings, transactional engine restart with rollback, and attributable audio state/receipts. | `.loom/tied/1-audio-config-design/` |
| 1.12 | 2026-07-24 | Node logging facility (§4.2): additive engine-sent `/log <stream> <values…>` on 7770 — a patch appends one node-stamped, tab-separated line to a per-stream daily append-only file, fire-and-forget like `/store`, invalid stream names dropped with a warning. Purely additive; no existing term changes shape. Destination selection (internal/usb) and the Device-tab surface follow as a later revision. | thread `42-node-logging` |
| 1.13 | 2026-07-24 | Log-destination configuration (§6): additive exact-device `/all/os/to <uid> log-config <json>` → `/os/log-config <uid> <ok\|err> <json>`, a bounded `{"destination": "internal"\|"usb"}` choice persisted as `LOG_DESTINATION` in `bopos.config` — no engine restart, no rollback. `/os/report` gains a `log` object (`destination`, `effective`, `usb_present`); `usb` falls back to `internal` when the stick is absent, resolved per entry. Purely additive. | thread `42-node-logging` |
| 1.13 am. | 2026-07-27 | Patch-manifest presentation clarification (§8): all declared params appear on desktop Control and Device control surfaces; the existing `dashboard: true` field now gates only the simplified standalone facilitator/iPad surface. No manifest or wire shape changes. | stitch `1-full-manifest-visibility` |
