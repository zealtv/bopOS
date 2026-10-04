# bopOS OSC Contract

**Version 1.21** — in progress; base ratified 2026-07-07; latest revision 2026-10-04. The
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
convergence (update/checkout/fetch), the offboard peripheral-bus IO layer, event
scheduling, the sync/event plane, and the machinery that produces provided terms (clock offset
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
| `/e/*` | **patch identities / framework scheduling** | targetable, patch-declared events with 0–3 free-form float elements (§3.2); well-formed undeclared identities are still scheduled |
| `/pt` (canonical `/point`) | framework/dashboard | point geometry broadcast — moving sound sources, arbitrary count; each device decomposes locally (§4.1) |
| `/p/*` | **patch** | patch-declared parameters — the only place output semantics live; numeric params also accept the framework-owned automation grammar (§3.3) |

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

### 3.1 Sync plane (clock-sync)

Forward clock sync so events fire sample-tight(ish) over WiFi, engine-agnostically.
The mechanism (HB-style) and design reasoning live in the `clock-sync` thread;
this is the pinned wire shape for `/sync/*`.

| address | direction | transport | args |
|---|---|---|---|
| `/sync/ping` | leader → fleet | broadcast, 6660 | `<seq:int32> <leaderTimeNs:string>` |
| `/sync/pong` | node → leader | unicast, 5550 | `<seq:int32> <leaderTimeNs:string> <uid:string> <deviceTimeNs:string>` |
| `/<id>/sync/offset` | leader → node | unicast | `<offsetNs:string>` |

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
- **Encoding:** every time-valued arg is the decimal string of an integer
  nanosecond count from `time.monotonic_ns()` — never a single 32-bit OSC float
  (§12), exact across the two Python endpoints, human-readable in a log, and
  full-resolution. `seq` is a plain int32. Monotonic, not wall clock: NTP
  steps must never glitch an event.
- **Grammar:** `/sync/ping` is the one framework address that omits
  the selector — broadcast-only and always fleet-wide. `/sync/pong` is a 2-part
  node→controller reply like `/hb`; `/<id>/sync/offset` is the normal 3-part
  `/<selector>/<plane>/<member>` (selector always a concrete `<id>`).

### 3.2 Event plane (`/e/*`)

Events reuse the §3.1 forward clock and offset. The patch owns declared event
identities and their element meanings; the framework owns target matching,
scheduling, and selector/time removal. This is the contract's first
split-owner plane.

Leader → fleet (6660):

```
/<selector>/e/<identity> <sharedTimeNs:string> [<e0:float> [<e1:float> [<e2:float>]]]
```

Node → engine (localhost 6661), at the local deadline:

```
/e/<identity> [<e0:float> [<e1:float> [<e2:float>]]]
```

- `<identity>` has the `/p/*` segment grammar: 1–8 non-empty
  `[A-Za-z0-9_-]+` segments and at most 255 ASCII bytes when slash-joined.
  Nesting is preserved and wire indices are 0-based by default.
- The element list has arity 0–3. Elements are free-form 32-bit OSC floats,
  identified by 0-based position; meanings such as note/velocity/duration are
  patch convention, not framework semantics. A zero-element fire has no engine
  arguments.
- `sharedTimeNs` is the decimal string of an integer leader
  `monotonic_ns()` count and always comes first because the element list is
  variable-length. The engine never receives it.
- The exact string `"0"` is the fire-on-arrival sentinel. A node bypasses the
  scheduler and sends the relative engine fire immediately. All other values
  use `deadlineNs = sharedTimeNs + offsetNs` and the §3.1 late-grace policy.
  Thus installation `event_lead_ms == 0` means synchronization is off without
  depending on a packet arriving inside the late grace.
- Nodes schedule every well-formed fire without consulting the manifest.
  Dashboard surfaces badge undeclared identities as they do for `/p/*`;
  declaration is documentation and authoring metadata, not a delivery gate.

### 3.3 Parameter automation grammar (`/p/*` plane)

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

Eight ports; 5551 and 7771 added in v1.21. The three LAN ports
are the public contract; the five localhost ports are one device's internal plumbing. As of
v1.2 **`bopos.py` is the node's only LAN citizen**: it alone binds 6660 and
sends on 5550 and the leased development stream port 5551. Engines — PD
included — live entirely on the localhost ports.
(Supersedes v1.1 §4/§4.1, which kept PD's direct 6660 path; that path was
retained only as a migration safety net and was removed after the relay,
helper-death, and production-macOS N=1 gates passed, 2026-07-12.)

| Port | Listener | Sender | Scope |
|---|---|---|---|
| 5550 | dashboard | bopos.py | LAN broadcast, fleet → dash |
| 5551 | dashboard | bopos.py | LAN unicast: leased development IO value streams to the requesting dashboard (§6) |
| 6660 | bopos.py (sole binder) | dashboard | LAN broadcast, dash → fleet |
| 6661 | engine (`[bopos]` in PD, OSCdefs in SC, …) | bopos.py | localhost: the selector-stripped engine surface (§4.2) |
| 6662 | engine | io/main.py | localhost: peripheral streams and control replies |
| 7770 | bopos.py | engine | localhost: engine requests only (§4.2) |
| 7771 | bopos.py | io/main.py | localhost: IO control replies; copies of original value bundles while a stream is leased |
| 8880 | io/main.py | engine, bopos.py | localhost: I/O commands |

Production engines listen on 6661; an audition instance is assigned its own
port via `BOPOS_ENGINE_PORT`, feeding exactly the same selector-free surface —
the topology is identical, only the port number moves.

**Transport discipline:**

- **Broadcast** only for low-rate, idempotent, genuinely one-to-many messages:
  `/hb`, `/os/assign`, `/all/*` admin and membership, targetable `/e/*`,
  `/pt`, `/os/mute`,
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
- `/e/*` (§3.2) has split ownership: the patch declares identities and meanings,
  while bopos.py matches targets and performs the clock math before delivering
  a selector-free, time-free fire.

### 4.2 The engine surface

The whole engine-facing contract, both directions (ratified 2026-07-12).
Engine-received, on the assigned engine port (default 6661), always
selector-stripped:

```
/id <n:int32>                  resolved identity (pushed on assignment and
                               unassignment, after a /config request, and
                               on engine-ready replay; -1 means unassigned)
/os/master <0..1>              the master term (§4.1)
/p/<segment>[/<segment>...] <values…>
                               patch-declared parameters (§8)
/pt <point> <element> <value>  shaped point scalars (§4.1)
/e/<segment>[/<segment>...] [<e0> [<e1> [<e2>]]]
                               scheduled relative event fire (§3.2)
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
                               action ∈ {update-bopos, shutdown, reboot}
                               — routes to the node's existing framework
                               update, shutdown and reboot behaviour (the
                               same code paths the dashboard verbs use in
                               python/bopos.py). No selector, no reply to the
                               engine — these actions are terminal or
                               restart the engine anyway; outcome receipts
                               continue to flow to the LAN model where
                               applicable (§7). Unknown actions, including
                               the removed update-patch action (v1.19), are
                               ignored with a logged warning, never fatal.
```

In PD this surface is owned by the `[bopos]` abstraction (`pd/bopos~.pd`),
which exposes the buses `bopos-context`, `bopos-master`, `bopos-param`,
`bopos-point`, `bopos-notify`, `bopos-io` and consumes
`to-bopos-io`, `to-bopos-report`. Other engines speak the wire directly
(`patches/demo-sc` is the reference). The PD-side bus plumbing for `/admin`
(e.g. a `to-bopos-admin` bus consumed by `[bopos]`) is not yet wired in
`pd/bopos~.pd` — that patch edit is Bob's to add; agents never edit `.pd`
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
32-bit; see `.glean/findings/pd-float-precision.md`). Patch name is already delivered
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
be sent as OSC floats or used by engines for synchronized event timing; bopOS
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
/all/os/performance <0|1>    → /os/report <json> (each responding node, unicast)
/all/os/to <uid> enabled <0|1> → /os/enabled <uid> <device-enabled> <output-enabled>
/all/os/to <uid> hostname <name> → /os/hostname <uid> <name> <ok|err>
/all/os/to <uid> audio-config <json>
    → /os/audio-config <uid> <ok|err> <phase> <json>
/all/os/to <uid> log-config <json>
    → /os/log-config <uid> <ok|err> <json>
/all/os/to <uid> wifi-config <json>
    → /os/wifi-config <uid> <ok|err> <phase> <json>
/all/os/to <uid> io-scan       → /os/io-scan <uid> <io-json>
/all/os/to <uid> io-write <json>
    → /os/io-write <uid> <ok|err> <json>
/all/os/to <uid> io-reinit <name>
    → /os/io-reinit <uid> <ok|err> <json>
/all/os/to <uid> io-stream <0|1>
    → /os/io-stream <uid> <ok|err> <json>       unicast receipt on 5550
/io/stream <uid:string> <bundle:OSC blob>      leased values, unicast on 5551
/os/io-error <uid> <name> <reason>  unsolicited, LAN broadcast to 5550
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
  alarm**; leased development IO values use their separate port below.
- `/os/report` returns the static facts as JSON: hostname, engine, has_i2c,
  has_wifi, audio_channels, screen, active patch, uptime, git-rev,
  update_model, contract-version, the sorted `groups` array, persistent
  `device_enabled`, execution `mute_all`, effective `output_enabled`,
  persistent boolean `performance`, and the `audio`, `log`, redacted `wifi`,
  and `io` (§11) objects below. This
  is the capability story: **pull, not broadcast.** The groups fact is reconciliation
  evidence; `/os/groups` is the immediate write receipt.
- **Performance (v1.21)** is the explicit global session switch, independent
  of Live / Simulation / Patch Edit and show playback. First installs start
  in development (`0`). Each node persists the value only on change and
  remembers it across reboot, including ephemeral engine-store nodes. There
  is no timeout. `/all/os/performance` is literal fleet-wide, accepts only
  numeric `0` or `1`, and is never refused because Performance is active.
  Its confirmation is the existing uid-bearing `/os/report` with boolean
  `performance`. The host saves its own global mode independently of projects
  and re-sends it when a device appears or reports a different mode.
  Devices enforce the locks: probes, operator module writes (`io-write`),
  development sensor streams (`io-stream`), stream-to-editor, Wi-Fi changes,
  and patch distribution/switch/removal. Assets and show-time audio controls
  remain available. Patch fetch refusals return `/os/fetched <slot> err`;
  patch switch/removal return the existing `/os/rev` error receipt with phase
  `performance`; Wi-Fi returns its existing error receipt with that phase.
  Operator `io-write` returns `/os/io-write <uid> err` with JSON
  `{"name","command","error":"performance"}`. This is an administrative
  refusal: it never marks a module errored or emits `/os/io-error`.
  `io-stream` returns `/os/io-stream <uid> err` with
  `{"active":false,"error":"performance"}`; entering Performance closes
  an open stream immediately and cancels the dashboard's consumer renewer.
  Read-only `io-scan` and repair `io-reinit` remain allowed. Queued writes are refused on entry;
  a write already sent to the bridge keeps its normal terminal receipt.
  Probes are silently unanswered. The dashboard also blocks Monitor sends,
  pushes, Set Live, New Version, manifest saves, and Patch Edit (including
  viewing); entering Performance stops an already-open editor. Development
  IO writes and streams use the same device-side predicate.
  Node `/log` entries and both service stdout/stderr sinks use RAM only in
  Performance: tmpfs on Linux, bounded process memory where tmpfs is absent.
  The configured log destination is retained; `log.effective` is `ram` until
  Performance ends. RAM entries are never copied back to SD or USB. The
  transition's mode write is intentional; this is a logging guarantee, not
  a read-only-filesystem mode. Actual Pi SD-write cessation still requires
  hardware verification.
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

### Exact-device IO control (v1.21, additive; in progress)

These verbs use only the literal `/all/os/to <uid>` envelope, including for
unassigned devices. `io-scan` takes no arguments, rescans fixed bus 1 in the
bridge, then returns the complete §11 `io` object unicast to the requester on
5550. No bus, not scanned, and a scanned empty bus are distinct facts.
`io-modules` was dropped: scans and `/os/report.io` already carry the registry.

`io-write` takes exactly one JSON object with `name`, `command`, and `args`
(an array of OSC scalar values). It addresses the existing driver through
`/io/<name> <command> <args…>` on localhost 8880. The terminal JSON reply has
exactly `name`, `command`, and `error`; `ok` carries `error: null`, and `err`
carries a §11 peripheral reason or the administrative refusal `performance`.
In Performance, valid writes return `err` with
`{"name":"<requested module>","command":"<requested command>","error":"performance"}`
without touching the driver, marking the module errored, or emitting
`/os/io-error`. Invalid payloads return `invalid-arguments` without
touching a driver. The node keeps one scan and one mutation outstanding,
queuing writes and Re-init together; a successful write is acknowledged only
after `/io/written`.
Entering Performance refuses queued writes immediately; the gate is also
rechecked before every queued write is sent. A write already sent to the
bridge retains its terminal receipt and timeout attribution. Refused writes
are discarded rather than replayed when Performance ends; scans stay allowed.
After 3 seconds without a local receipt (`BRIDGE_REPLY_TIMEOUT_SECONDS`), the
node drops that request and serves the next without emitting any timeout reply
or new reason token. The dashboard expires its own pending scan/write after
4 seconds (`IO_REQUEST_TIMEOUT_SECONDS`), marks `phase:timeout` internally and
refreshes the report. These deadlines do not change the wire vocabulary.

Bridge errors also travel as unsolicited `/os/io-error <uid> <name> <reason>`
on the normal fleet → dashboard path, LAN broadcast to 5550. The dashboard
stores the IO facts and receipts and broadcasts the observed state to clients.
IO value streams use the dedicated port below; control replies and heartbeats
remain on 5550. Performance enforcement is shared with §6.

**Per-module Re-init.** `/all/os/to <uid> io-reinit <name>` takes exactly one
valid, non-reserved module name. It repairs declared modules only: the bridge
reads the type and address from the device's active manifest, retires the
target instance and runs its setup again under the same IO lock as writes,
polls and scans. Other module instances and registry rows are untouched.
Unlike a matching `/io/create`, this repair actually recreates a running
instance. **Allowed in Performance**, as a repair action.

`/os/io-reinit <uid> <ok|err> <json>` returns unicast on 5550 with exactly
`{"name":"<name>","error":null|"<reason>"}`. Success has `ok,error:null`;
failure has `err` and an existing reason: `invalid-arguments` for a malformed
request, `unknown-command` for an undeclared target, `no-bus` for an unusable
bus, or `create-failed` for an absent chip or failed retirement/setup. Missing
hardware remains `missing` with null registry error; retirement/setup failure
is `errored` with `create-failed`; success is `running` with null error.
Malformed and undeclared requests do not change a live instance's health.
Bridge registry and error updates retain their existing paths. Writes and
repairs share the node FIFO so one `/io/error <name> <reason>` completes one
active mutation. On entry into Performance, queued writes are refused but
queued repairs remain. The same three-second silent node receipt timeout and
four-second dashboard timeout apply; timeout adds no wire reason. The Device
tab offers Re-init per row, disabled offline, pending or when the module is
not declared; receipt and report updates refresh its state.

### Leased development IO streams (v1.21, additive)

`/all/os/to <uid> io-stream <0|1>` opens/renews (`1`) a ten-second lease or
closes (`0`) it. It accepts exactly one OSC integer `0` or `1`. The unicast
`/os/io-stream <uid> <ok|err> <json>` receipt on 5550 has exactly
`{"active":boolean,"error":null|"performance"|"invalid-arguments"}`.
Successful open/renew returns `ok` with `active:true`; close is idempotent and
returns `ok` with `active:false`. Both have `error:null`. In Performance both
valid requests return `err` with `active:false,error:"performance"`.
Malformed requests return `err` with `error:"invalid-arguments"` and the
current lease state, without changing it. These administrative refusals never
mark modules errored or emit `/os/io-error`.

There is one lease per device. The latest successful `1` replaces its sole
destination with that requester's IP and renews the lease. Development `0`
closes it regardless of requester. Expiry and entering Performance stop it;
leaving Performance does not reopen it. While leased, each original bridge
poll bundle is copied to localhost 7771 and forwarded on UDP 5551 as one
`/io/stream <uid:string> <bundle:OSC blob>` message (typetags `,sb`). The blob
is the complete original OSC bundle, preserving module addresses, argument
types, ordering and bundle boundaries. Rate is at most the bridge's poll rate
(default 10 Hz). Ordinary engine delivery on 6662 continues throughout.

The dashboard listens on 5551 and exposes server-side
`subscribe_io(uid, consumer, callback)` / `unsubscribe_io(uid, consumer)`.
Consumers share one device at a time; a second device is rejected locally
while the first has consumers. Each callback receives the original bundle
bytes and a map of module names to value lists. The dashboard renews every
three seconds while consumed; the last unsubscribe closes it and cancels
renewal. Performance and dashboard shutdown clear consumers. No stream is
opened without a consumer. Live module panels now consume this seam through the
Monitor transport broker; editor forwarding remains a subsequent increment.
The Device tab's **Show in Monitor** checkbox opens a driver-described panel in
the dock's **Modules** tab. Inputs show original patch-received numbers, units
and bounded sparklines; outputs use the existing exact-device `io-write` verb
and receipts. Each panel names its device and live source. Hidden/collapsed
panels retain the local choice but release visual interest. The dock or one
panel can pop out to an ordinary browser window with its own broker selection.
Operator writes and visual streaming are refused in Performance. This stream
does not reinstate framework meter telemetry.

Local bridge copying is controlled on 8880 by `/io/stream <0|1>` with its own
ten-second lease. The node renews it with each accepted open/renew and sends
`0` on close, expiry, shutdown or entry into Performance. The independent
bridge timeout bounds copying after node failure or a lost close. `stream`
is reserved as a module name, alongside the existing bridge verbs.

### Exact-device Wi-Fi configuration (v1.20, additive)

`/all/os/to <uid> wifi-config <json>` → `/os/wifi-config <uid> <ok|err>
<phase> <json>`. The request is the complete ordered list of bopOS-managed
WPA-Personal networks plus the Wi-Fi country; list order is priority.
Each network carries `ssid`, `hidden`, `enabled` and `psk`, where `psk: null`
keeps the device's existing secret. Invalid, partial or duplicate lists, and
lists with no enabled network, reject whole. The node applies through a
pre-provisioned argument-less privileged helper, replies, then lets the
network manager re-evaluate; there is no rollback. Receipts and `/os/report`
carry a redacted `wifi` object (`managed`, `country`, `active`, `networks`
with `secret: true|false`, `unmanaged` SSIDs) and never a passphrase.
**Trust:** the request travels as an installation-LAN broadcast like every
exact-device verb, readable by any host on that network; it is intended for
provisioning on an operator-controlled network only, and the dashboard
warns before any send that carries a passphrase. Devices in the field
join only hidden, passphrase-protected networks.

The complete request has exactly `country` (an ISO 3166-1 alpha-2 code) and
`networks` (an ordered array). Each row has exactly `ssid` (1–32 UTF-8 bytes,
unique in the list), `hidden` and `enabled` (booleans), and `psk` (null or
8–63 printable ASCII characters). Missing, extra or wrongly typed fields,
unknown country codes, duplicate SSIDs, out-of-range values, no enabled
network, or a null PSK without an existing device secret reject the whole
request as `invalid`. Open networks, enterprise Wi-Fi, Ethernet and static
IP settings are outside this form.

```json
{"country":"GB","networks":[{"ssid":"show-1","hidden":true,"enabled":true,"psk":null}]}
```

Receipts use phases `applied`, `invalid`, `unavailable` (no Wi-Fi or no
installed/authorized helper), or `failed` (helper/network manager refused).
`ok` pairs with `applied`; all other phases pair with `err`. The receipt JSON
and report `wifi` field have the same redacted shape:

```json
{"managed":true,"country":"GB","active":"workshop","networks":[{"ssid":"show-1","hidden":true,"enabled":true,"secret":true}],"unmanaged":["imager-net"]}
```

`active` is the currently joined SSID or null. Without Wi-Fi or a helper the
object is exactly `{"managed":false}`. Listing an unmanaged SSID adopts its
profile into bopOS control; profiles not listed for adoption are never
deleted. Disabled managed profiles retain their secrets but are never
joined. The privileged helper accepts no arguments and reads the request
from stdin; `--status` returns only the redacted object. Passphrases never
enter process arguments, node config or persistence, reports, receipts,
dashboard console taps, public WebSocket state, project or venue files.
After `applied`, a network change may briefly drop the device; its returning
heartbeat confirms it is back. Recovery is physical, without rollback.

## 7. Admin and convergence (`/os/*` verbs)

Lifecycle verbs always mean one thing: `/os/reboot`, `/os/shutdown`,
`/os/restart-engine` (targeted; replaces pkill-everything — `stop.sh`'s
`pkill python` is retired).

Provisioning verbs are **convergence assertions**, not filesystem operations —
WHAT is fixed by the contract, HOW is chosen by the node's `update_model`:

- `/os/updatebopos` updates the bopOS framework only — persistent: git pull +
  reboot (today's behaviour). Ephemeral: re-fetch the mutable layer and re-exec,
  or honestly no-op. The old `/os/update` spelling has no alias.
- `/os/checkout <branch>` selects and converges the bopOS framework branch;
  it does not update patches.
- `/os/patch <name>` keeps the OS and helper online: stop the current engine
  stack, select the validated installed patch, launch its engine, then send the
  provisioning receipt. It uses the installed bytes without a Git pull and
  never reboots the device.
- Patches reach devices through dashboard push using `/os/fetch` with a
  `patch:<name>` slot (§9). `/os/addpatch` and `/os/pullpatch` are removed;
  there are no aliases or compatibility handlers.
- `/<id>/os/patches` → `/os/patches <json>` (unicast) lists installed
  patches as objects `{name, active, manifest}`. The two flags are
  booleans; `manifest` means `bopos.patch.json` is present and valid.
  The former `git` field is removed; patches have no Git deployment mode.
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
    {"path":["instrument","marimba"], "name":"gain", "kind":"float", "min":0, "max":1, "default":0.75, "dashboard":true},
    {"name":"backing", "kind":"float", "min":0, "max":1, "default":0.8},
    {"name":"echo",    "kind":"toggle", "default":0} ],
  "events": [
    {"name":"snap", "arity":0, "description":"Fire the snap gesture"} ],
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
- **`kind` (required; hard break 2026-07-28):** one of `float`, `int`,
  `toggle`, `enum`, or `text`. `float` and `int` carry numeric
  `min`/`max`/`default`; `toggle` carries a `0`/`1` default and derives its
  range (authoring `min`/`max` is invalid); `enum` carries `options` plus an
  integer-index default and derives `0`…`n-1`; `text` may carry a string
  default. Their unchanged OSC tags are respectively `f`, `i`, `i`, `i`,
  and `s`. The old `type: "f"|"i"|"s"` declaration key is rejected loudly.
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
  verbs** is *never* a manifest concern: a project-level allowlist in
  `project.json` (`"facilitator_commands": […]`, **default empty**)
  opts specific verbs onto the surface, confirm-gated, with destructive
  convergence verbs (updatebopos/checkout/reboot/shutdown) at minimum
  hold-to-confirm. The patch promotes its params; the project promotes its
  verbs. Loaders accept the legacy `facilitator` spelling and normalize it to
  `dashboard`; saves emit only `dashboard`. If both spellings are present with
  conflicting values, the manifest is invalid.
- **`options` (required on `kind: "enum"`; revised 2026-07-28):** a
  list of 2–64 unique labels (1–32 characters, no newlines) naming its
  indices — an *enum*. **The wire does not change:** the value is the integer
  index, sent, replayed, persisted and automated exactly as any other integer
  (§3.3 generators emit indices, quantized by the same path). `min`/`max` are
  **derived** from the option count (`0`…`n-1`); an authored pair that
  disagrees is invalid, so a saved manifest round-trips. Only the control
  surface reads the labels.
- **`events` (optional; wired in v1.14):** a top-level
  list beside `params`, each `{"name": …, "path": […], "arity": 0|1|2|3,
  "defaults": […], "dashboard": bool}`. `name`/`path` qualify
  exactly like a param; `/p/*` and `/e/*` are distinct planes, so the same
  qualified identity may be declared once in each. An event carries **one
  label — its `name`**; elements are free-form floats named only by 0-based
  position (per-element `labels` were retired 2026-07-28, Bob). What an
  element means — note/velocity/duration is the common case — is patch
  convention, not an enforced framework meaning. Fires use `/e/*`
  (§3.2), always forward-synchronized unless the installation-wide
  `event_lead_ms` is `0`. A zero-element event is a momentary named fire.

**`io_modules` (optional; v1.21):** a top-level list of declarations, for example
`[{"name":"adc","type":"ads1115","address":"0x48"},
{"name":"tilt","type":"lis3dh","address":"0x19","optional":true}]`.
Names are unique, nonempty single OSC segments and cannot be bridge verbs
(`create`, `poll`, `report`, `scan`, `bridge`). Types name a supported host
driver. Addresses are hex strings in `0x03`–`0x77`, normalized to lowercase.
`optional` is a boolean, default false. The manifest is fleet-wide; presence
is resolved separately on each device. The Patches manifest editor authors
these declarations. Driver descriptions live beside the driver code and the
dashboard reads its host copy without importing hardware libraries.

### 8.1 Retired host-side facility

Retired 2026-10-03 (v1.18). The former host-side saved-parameter facility is
removed. Live controls and Show messages use ordinary §3.3 parameter traffic;
no replacement storage format, reference message or wire verb is introduced.
The v1.17 definition is historical; see §15.

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
  framework-owned, engine-neutral directory **outside the patch directory** —
  `~/bopOS/assets/<slot>/`. At launch, bopOS hands every installed slot to the
  engine as its absolute folder path through the §4.2 list
  (`bopos-context assets <absolute-path...>` for PD, JSON-array
  `BOPOS_ASSETS` for other engines). Distribution and inventory continue to
  address each slot by its `<slot>` basename. The retired
  `patches/<active>/bop/samplepacks` compatibility symlink is not created;
  every asset consumer uses the run-context slot paths directly.
- **Patch landing convention:** `patch:<name>` lands in
  `~/bopOS/patches/<name>/` with the same diff, resume, hash-verification and
  prune-to-manifest convergence semantics as an asset slot. An existing
  Git-cloned patch directory is treated as ordinary installed content:
  a successful fetch replaces its bytes with the host's distributable content
  and removes its local `.git` directory or `.git` file. A `.git` file's
  external target is not followed or removed. The replacement is converged and
  manifest-validated in staging before installation; fetch or validation
  failure preserves the existing directory, including its Git metadata, and
  installation failure restores it. Existing path and symlink safety checks
  still apply. Git metadata is not distributed from the host.
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
- **Manifest owns declared modules** (v1.21). At engine readiness, `bopos.py`
  sends the existing `/io/create <name> <type> <address>` for each declaration.
  The bridge reads the same active manifest: a matching create of an already
  running declaration succeeds as a no-op; a conflicting type/address returns
  `create-failed` without replacing the live chip. Legacy dynamic creates still
  work for undeclared names. Changed or removed declarations retire their old
  instances when the active manifest is reconciled. Writes remain last write
  wins under the shared bridge lock.
- **Inspection is demand-driven** (v1.2; supersedes the 2026-07-08
  `role: "meter"` republish model, which was deleted with the meter plane): a
  patch retains values it wants inspectable via engine-side `/report <name>
  <values…>` (§4.2), and the dashboard pulls them one-shot with `/os/probe`
  (§6). That retained-value path has no subscription stream or periodic
  republish. The leased development IO stream (§6) is the sanctioned exception
  for live module values, refused in Performance. Retained reports have no
  presentation metadata; a future reporting UI must design explicit read-only
  semantics from concrete needs.
- No-bus is a declared legal state: `io_buses: []`, `/io/scan` → empty,
  `/io/create` → `/io/error <name> no-bus`. (`sys_i2c` must degrade the way
  `sys_wireless` already does.)

**Control reply model (v1.21).** Every bridge reply goes to both engine 6662
and `bopos.py` localhost 7771; failed delivery to either does not suppress the
other. Poll value bundles always go to 6662 and are copied intact to 7771
only while the development stream lease is active (§6).
The legacy `/io/scan <integer-address>…` reply is retained. The added local
control grammar is:

```
/io/scanned <io-json>
/io/registry <json>
/io/error <name> <reason>
/io/written <name> <command>
/io/reinitialized <name>
```

`/io/scanned` carries the complete IO object after scanning. `/io/registry`
carries that same complete object on `/io/report`, registry changes and module
status changes. `/io/written` confirms the driver write returned successfully.
Local `/io/reinit <name>` on 8880 repairs the named active-manifest declaration
under the IO lock; `/io/reinitialized <name>` confirms its setup returned
successfully, after the refreshed registry. Failure uses the existing
`/io/error <name> <reason>` and registry health rules in §6. `reinit` is a
reserved module name alongside the other management verbs.
The node holds the latest object for `/os/report.io`. Scanning stays in the
bridge and skips live peripheral addresses under the shared IO lock.

**IO object**, one shape for `/os/report.io`, `io-scan` replies and dashboard
state (ratified proposal §8a):

```json
{"bus":1,"scanned":true,"addresses":[{"address":"0x1a","claimed":true},{"address":"0x48","claimed":false}],"modules":{"adc":{"type":"ads1115","address":"0x48","state":"running","error":null}}}
```

`bus` is fixed `1`, matching the drivers, or `null` when no usable bus can be
opened. `scanned` is false until a scan has run. `addresses` is sorted by
address; addresses are lowercase hex strings, and `claimed` records kernel
ownership (`UU`). A usable but empty scanned bus has `bus:1`, `scanned:true`
and `addresses:[]`. Modules map names to `type`, `address`, `state` and `error`.
State is `running`, `errored`, or `missing`. An absent declared address or
unusable bus is `missing`; a present chip whose setup fails is `errored`.
Optional absence is normal; required absence also emits `create-failed`
(or `no-bus`). Error is null or one of the reasons below. Read failures mark
the module errored with null error and one log line naming the module/address;
a successful subsequent read restores running. Registry/report health is
authoritative: rejected requests do not themselves replace module health.

**Errors.** `/io/error <name> <reason>` uses only `no-bus`, `create-failed`,
`invalid-arguments`, `unknown-command`, and `write-failed`. `bridge` is a
reserved module name for errors without a module target, including malformed
poll/scan arguments and unnamed create requests. Named malformed creates use
the requested name with `invalid-arguments`; import/setup/type failures use
`create-failed`. Unknown targets use `unknown-command`; missing peripheral
commands or extra address segments use `invalid-arguments`; raised driver
writes use `write-failed`. Errors relay to the dashboard through §6.

## 12. Hard constraints

- **PD OSC floats are 32-bit** (~6–7 significant figures). Any value needing more
  crosses the wire as a **string** (uids, versions, epoch/shared times). Absolute
  wall-clock timestamps are never sent as OSC floats and never used by engines
  for synchronized event timing: the synced clock lives in Python; engines
  only ever receive a bare relative fire. `/<selector>/e/<identity>
  <sharedTime-as-string> [elements…]` is converted by bopos.py before the
  engine sees it. Civil
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
alarm); envelope-carrying events (crossfades are dashboard param automation);
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
| 1.8 | 2026-07-19 | Parameter-automation grammar (§3.3): generator-slot model on numeric `/p/*` params — constants, string-unit timed fades, `loop`, `stop`, clock-anchored idempotent LFOs, `c:`/`p:`/`f` option shorthand, floor-and-emit-per-crossing ints, fades catching up as computed constants. Decomposition in bopos.py; Bob's 2026-07-20 audible ruling clarifies that engines receive scalar control ticks only, so existing patches remain unchanged. String/mixed-array kind explicitly deferred (name and plane open). | `.lore/items/2026-07-19-param-automation-design-ratified/`; stitches `automation-0-design-ratification`, `aa-2a-scalar-engine-frames` |
| 1.8 am. | 2026-07-19 | Patch-manifest presentation tidy (§8): promotion key renamed `facilitator` → `dashboard` with compatible normalization and conflicting dual-key rejection; retired `group` is ignored on load and stripped on save. | stitch `p7-patch-tab-tidy` |
| 1.8 am. | 2026-07-20 | Engine group-context amendment (§4, §4.2): the node's current Seat-group membership joins run context, delivered at launch and re-delivered after every successful, durably-persisted membership change (including assignment/unassignment clears). Wire shape is sorted OSC ints or the single sentinel `-1`; PD's `bopos-context groups <int...>` bus and the new `/groups <int...>` engine-received term keep non-PD engines boundary-equivalent via `BOPOS_GROUPS` and the same live `/groups` message. Purely additive — no existing term changes shape. | stitch `engine-group-context` |
| 1.9 | 2026-07-23 | Multi-asset-slot run-context revision (§4.2, §9): the engine receives the deterministic list of absolute installed-slot folder paths instead of one assets root. PD gets `bopos-context assets <absolute-path...>`; other engines get the same list as JSON-array `BOPOS_ASSETS`. Intentional scalar-root-to-list migration. | stitch `1-context-list-design` |
| 1.10 | 2026-07-23 | Physical/execution routing revision: exact-device `mute` becomes positive `enabled`, reports `device_enabled`, `mute_all`, and `output_enabled`, and execution transitions cannot replay physical-device state. MUTE ALL remains execution-scoped like master. | thread `37-physical-device-control-routing` |
| 1.11 | 2026-07-23 | Exact physical-device audio configuration: detected ALSA cards only, complete validated JACK settings, transactional engine restart with rollback, and attributable audio state/receipts. | `.loom/tied/1-audio-config-design/` |
| 1.12 | 2026-07-24 | Node logging facility (§4.2): additive engine-sent `/log <stream> <values…>` on 7770 — a patch appends one node-stamped, tab-separated line to a per-stream daily append-only file, fire-and-forget like `/store`, invalid stream names dropped with a warning. Purely additive; no existing term changes shape. Destination selection (internal/usb) and the Device-tab surface follow as a later revision. | thread `42-node-logging` |
| 1.13 | 2026-07-24 | Log-destination configuration (§6): additive exact-device `/all/os/to <uid> log-config <json>` → `/os/log-config <uid> <ok\|err> <json>`, a bounded `{"destination": "internal"\|"usb"}` choice persisted as `LOG_DESTINATION` in `bopos.config` — no engine restart, no rollback. `/os/report` gains a `log` object (`destination`, `effective`, `usb_present`); `usb` falls back to `internal` when the stick is absent, resolved per entry. Purely additive. | thread `42-node-logging` |
| 1.13 am. | 2026-07-27 | Patch-manifest presentation clarification (§8): all declared params appear on desktop Control and Device control surfaces; the existing `dashboard: true` field now gates only the simplified standalone facilitator/iPad surface. No manifest or wire shape changes. | stitch `1-full-manifest-visibility` |
| 1.14 | 2026-07-28 | Additive targetable `/e/*` event plane (§3.2): patch-declared identities with 0–3 floats, framework-owned forward scheduling, selector-free/time-free engine fires, and exact `"0"` fire-on-arrival sentinel. Installation setting `cue_lead_ms` becomes `event_lead_ms` with load-only fallback. `/cue` remains unchanged for its separate retirement stitch. | thread `44-event-plane` |
| 1.15 | 2026-07-28 | Hard-break retirement of the `/cue` plane and the manifest `cues` key. Zero-element `/e/*` events replace named fires in full; no compatibility alias, deprecation path, or show-document migration. | thread `44-event-plane` |
| 1.16 | 2026-07-28 | Manifest event-element `labels` retired (§8): an event carries one label, its `name`; elements are numbered 0-based floats with optional `defaults`. Authoring surfaces stopped requiring a name per element. Stale `labels` keys are stripped on read, not rejected. | Bob, live session (thread `44-event-plane`) |
| 1.17 | 2026-07-29 | Preset foundations, host-side and additive — **no wire form is added**. New §8.1 states that a preset is a sparse map from parameter identity to the `/p/*` argument list that reproduces it, applied as ordinary fan-out; defines the canonical parameter-schema fingerprint (`{identity, kind, min, max, options}` projection, sorted by identity, ordered enum labels, SHA-256); states that a capture holds declared params only, never events, never site-layer state, and records intended dashboard state rather than observed node output; and pins that a timed apply reuses the existing §3.3 fade form for `float`/`int` while every other kind sets full-state at t=0. §9 excludes `presets/` from the distribution manifest, the patch fingerprint, prune-to-manifest convergence, and the distribution HTTP surface, so saving a preset cannot restage the fleet patch. §3.2 and §3.3 are unchanged. **`morph` deferred, not overlooked:** an additive `morph <dur> [c:<n>] <spec…>` form interpolating generator argument vectors was designed, reviewed and ratified in outline, then dropped from v1 by Bob on 2026-07-29 because the workhorse case — sweeping scalars — is already the existing fade form, and the wire/engine risk served only generator interpolation. The settled design is parked in `feature-backlog/48-morph-interpolation`; nothing here forecloses it, since a preset entry already *is* the full-state argument list `morph` would consume. | `.loom/tied/1-preset-architecture-design/`; thread `41-preset-primitive` (`design-addendum.md`, `.loom/tied/3-addendum-review/review-2.md` §F1) |
| 1.18 | 2026-10-03 | Retire the host-side preset facility (§8.1): storage APIs, capture/recall UI and Show PRE references are removed. Remove §9’s special distribution, fingerprint, prune and HTTP exclusion for `presets/`; obsolete local files and test PRE cues are deleted without a compatibility layer. Installation and venue unknown fields are ignored; unsupported message kinds remain invalid. No wire grammar or engine behavior is added. | Thread `65-remove-presets`, `2-remove-presets` verification |
| 1.19 | 2026-10-03 | Retire the Git patch-deployment route (§4.2, §7, §9): remove `/os/addpatch`, `/os/pullpatch`, the engine `/admin update-patch` action and the `git` patch-inventory field, with no aliases or compatibility handlers. Patch selection uses installed bytes without a Git pull. Dashboard push through `/os/fetch` is the sole deployment route; a successful push converts an existing clone to ordinary installed content, removing its local Git metadata through staged, validated replacement with rollback on failure. Framework Git update, checkout and revision reporting are unchanged. Pin engine `/id` to int32 on assignment, unassignment, `/config` and ready replay (§4.2), preserving resolved values and the `-1` sentinel; real Pd confirms identical context delivery for float/int inputs. | stitch `68-remove-git-patch-route`, `proposal.md` and Bob's ratification ruling; stitch `10-engine-id-int`, Bob's conditional integer ruling and real-Pd verification |
| 1.20 | 2026-10-04 | **Exact-device Wi-Fi configuration (§6, additive).** `/all/os/to <uid> wifi-config <json>` → `/os/wifi-config <uid> <ok\|err> <phase> <json>`. The request is the complete ordered list of bopOS-managed WPA-Personal networks plus the Wi-Fi country; list order is priority. Each network carries `ssid`, `hidden`, `enabled` and `psk`, where `psk: null` keeps the device's existing secret. Invalid, partial or duplicate lists, and lists with no enabled network, reject whole. The node applies through a pre-provisioned argument-less privileged helper, replies, then lets the network manager re-evaluate; there is no rollback. Receipts and `/os/report` carry a redacted `wifi` object (`managed`, `country`, `active`, `networks` with `secret: true\|false`, `unmanaged` SSIDs) and never a passphrase. **Trust:** the request travels as an installation-LAN broadcast like every exact-device verb, readable by any host on that network; it is intended for provisioning on an operator-controlled network only, and the dashboard warns before any send that carries a passphrase. Devices in the field join only hidden, passphrase-protected networks. | `33b-device-network-config/1-network-config-design.tied/decisions.md` §8, Bob's ratification 2026-10-04 |
| 1.21 | 2026-10-04 | **in progress.** Ratified IO/Performance design: ports 5551/7771, IO control and development streams, manifest modules, remembered Performance mode. Shipped: dual local control replies, `io-scan`/`io-write`, unsolicited `/os/io-error`, the IO object and peripheral error vocabulary (§4, §6, §11); `io-modules` dropped. Global `/all/os/performance <0\|1>`, confirmed by boolean `/os/report.performance`, adds device-enforced development locks, host convergence, never-locked exit, RAM-only logging and `log.effective: ram`, independent of execution target and project with no timeout. Ratified refusal word `performance` applies to `/os/rev` and Wi-Fi phases and IO write/stream receipts, never module faults; queued writes recheck the gate and read-only scans remain allowed. Manifest `io_modules`, engine-start creation, idempotent matching creates, per-device missing/errored presence and host-readable driver descriptions ship (§8, §11). Leased IO transport ships (§4, §6): `io-stream` has ten-second node/bridge leases, `{active,error}` receipts and immediate Performance close; original bundles copy to 7771 and travel as `/io/stream <uid:string> <bundle:OSC blob>` on live unicast 5551. Dashboard consumers share one device, renew only while consumed, and release on Performance/shutdown; simfleet streams fake driver-shaped values. Per-module Re-init now ships (§6, §11): `io-reinit <name>` returns `/os/io-reinit <uid> <ok\|err> {name,error}`; local `/io/reinit` / `/io/reinitialized` repair only the active-manifest declaration under the IO lock, sharing the write FIFO and existing timeouts/reasons. Repair remains allowed in Performance, and the Device-tab button is disabled offline/pending/undeclared; simfleet has matching behavior. Live driver-described Modules panels, Device-tab Show in Monitor, ordinary dock/panel windows, and host-side Performance refusal of operator writes now ship through the existing Monitor broker and IO verbs; editor input remains a later increment. | `59-i2c-inventory/0a-io-design-review.tied/proposal.md` §2, §8, §8a, §8b, §8d and `rulings.md`; stitches `1-scan-transport`, `3-peripheral-lifecycle`, `77-performance-mode`; `8-stream-port.tied/proposal-stream-wire.md`, ratified 2026-10-04; `2-device-tab-inventory.stitching/reinit-verification.md`; `9-module-panels.stitching/instructions.md` |
