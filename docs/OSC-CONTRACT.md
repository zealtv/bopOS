# bopOS OSC Contract

Version 1.0 — ratified 2026-07-07. Provenance: five-expert council + judgment +
Bob's ratification, recorded in `.lore/` (`osc-schema-council`). This document is
the durable spec; the council record holds the reasoning and the rejected
alternatives.

## 1. Purpose and scope

bopOS moves control and identity between a controller (dashboard) and a fleet of
autonomous nodes. It guarantees each node can say **who it is, whether it's alive,
what it can do, and that it has converged to the intended revision** — always as
*declared facts*, never as hardware or disk assumptions.

The framework owns: identity/liveness, the OSC transport and namespace, convergence
(update/checkout/fetch), the offboard peripheral-bus IO layer, and the
sync/cue/spatial control plane. Everything that comes out of the speakers, LEDs,
printer, or monitor is the **patch's**; engine launch is **patch-declared**; media
IO (MIDI/HID/audio-in) is the **engine's**; control-plane state, spatial math, and
scene authoring are the **dashboard's**.

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

Nodes route on the selector exactly as today (`route-by-id`; `all` = everyone;
id −1 = unassigned). Replies carry the request's address, so a stray packet in a
log is self-describing.

### Planes

| plane | owner | contents |
|---|---|---|
| `/os/*` | framework | identity, liveness, admin, discovery, persistence, distribution (absorbs `/helper/*` and `/system/*`) |
| `/io/*` | framework | offboard bus peripherals (I2C today; verbs are bus-agnostic) |
| `/sync/*` | framework (Python) | clock offset — reserved; shaped by the clock-sync thread |
| `/cue` | framework (Python) | discrete scheduled fires; engines only ever see relative ms |
| `/pt` (canonical `/point`) | framework/dashboard | dumb spatial geometry `<x> <y> <radius>` — reserved |
| `/p/*` | **patch** | patch-declared parameters — the only place output semantics live |

The framework planes are a **closed set**; `/p/*` is open and entirely
patch-owned. `gain` `gain2` `backing` `echo` are patch parameters and live under
`/p/*` (bare `/gain` aliased one transition release).

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

## 4. Ports and transport

The six ports stay exactly as deployed. The two LAN ports are the public contract;
the four localhost ports are one device's internal plumbing, documented here so
they stop being magic numbers.

| Port | Listener | Sender | Scope |
|---|---|---|---|
| 5550 | dashboard | node (helper.py and PD) | LAN broadcast, fleet → dash |
| 6660 | PD (`bopos.osc.pd`) | dashboard | LAN broadcast, dash → fleet |
| 6661 | PD | helper.py | localhost reply |
| 6662 | PD | io/main.py | localhost reply |
| 7770 | helper.py | PD (`route helper` forward) | localhost |
| 8880 | io/main.py | PD (`route io` forward) | localhost |

**Transport discipline:**

- **Broadcast** only for low-rate, idempotent, genuinely one-to-many messages:
  `/hb`, `/os/assign`, `/all/*` admin, `/cue`, `/pt`, `/os/mute`.
- **Unicast to the requester** for all request/reply traffic: `/os/pong`,
  `/os/report`, `/os/params`, `/os/rev`, `/os/fetched`. (WiFi broadcast has no
  MAC-layer ACK and rides the lowest basic rate — it is scarce and lossy; replies
  don't wake 100 CPUs.)
- **Control-plane law: every fleet command is full-state and idempotent.** No
  increments. Re-sending anything is always safe — which is also what makes
  spamming `/os/mute` a valid safety procedure.
- The heartbeat is sent by **helper.py directly to 5550** (not through PD's
  netsend), so engine death ≠ device death.
- Spatial at fleet scale is the broadcast `/pt` with node-side falloff — never
  N× per-device gain streams. Dashboard-computed per-device `/p/gain` is the
  correct first implementation and remains fine ≤ ~12 nodes and on the audition rig.

## 5. Identity, assignment, persistence

- **`uid`** — an opaque stable string the node chooses: persisted machine token →
  primary-interface MAC (discovered, not `wlan0`-hardcoded) → per-boot UUID. On
  deployed Pis `uid == MAC`. IP is a return path, never identity.
- **Assignment** (`id`, `name`, positions) is set from the dashboard:

  ```
  /all/os/assign <uid> <id> <name> [posx posy pos2x pos2y]
  ```

  Idempotent full-state; positions ride in it (no separate verb). The matching
  node applies it, sets its hostname, tells the engine its id, and acks by
  heartbeating with the new id.
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
/all/os/mute <0|1>                                             (safety)
```

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
  sends must always converge on silence.

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
    {"name":"gain",    "type":"f", "min":0, "max":1, "default":0.75, "group":"mix"},
    {"name":"backing", "type":"f", "min":0, "max":1, "default":0.8,  "group":"mix"},
    {"name":"echo",    "type":"i", "min":0, "max":1, "default":0,    "group":"fx"} ],
  "caps": ["screen"], "slots": ["samplepacks"] }
```

- The manifest is the single source of truth for *what starts this patch*
  (engine/entrypoint — PD is the reference engine, not the required one) and
  *what can be controlled* (params). It is diffable, git-friendly, and
  agent-writable.
- helper.py serves it verbatim: `/<id>/os/params` → `/os/params <json>` (unicast).
- The dashboard **renders controls from the declaration** — no more hardcoded
  sliders. Values flow as `/<id>/p/<name> <value>` or `/all/p/<name> <value>`.
- Fail loud: no manifest → legacy three sliders with a visible "undeclared" badge;
  a `/p/*` value hitting an undeclared name gets a badge, not a guess. The
  launcher validates declared params before start so the manifest can't silently
  drift.
- **`role` (optional; additive, ratified by Bob 2026-07-08):** a param
  declaration may carry a `role` string naming what the param *is* to generic
  UIs. Defined roles: `"volume"` — the one param a facilitator volume card
  drives (at most one per manifest; fallback when absent: the param literally
  named `gain`; neither → the device card is status-only). `"meter"` — a
  read-only value the patch republishes outward as `/<id>/p/<name>` (§11);
  dashboards render it as a live meter, never a control, and never send it.
  Consumers ignore roles they don't recognise.

## 9. Distribution and landing

```
/<id>/os/fetch <source-uri> <slot>    →    /os/fetched <slot> <ok|err>   (unicast)
```

- `source-uri` dispatches on scheme: `http:` (the fleet-scale path — dashboard
  serves LAN HTTP with a manifest of files + hashes; nodes pull by diff with
  Range-resume; works air-gapped), `gdrive:` (legacy ingest), `file:`.
- **Landing convention:** assets land in a framework-owned, engine-neutral root
  **outside the patch git tree** — `~/bopOS/assets/<slot>/` — handed to every
  engine at launch (env var and an `ASSETS` startup message alongside the existing
  `ACTIVEPATCH`/`RANDOM` sends). PD, SC, and oF patches all read the same
  predictable root. Legacy `patches/<active>/bop/samplepacks` is symlinked for one
  release.

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
- No-bus is a declared legal state: `io_buses: []`, `/io/scan` → empty,
  `/io/create` → `/io/error <name> no-bus`. (`sys_i2c` must degrade the way
  `sys_wireless` already does.)

## 12. Hard constraints

- **PD OSC floats are 32-bit** (~6–7 significant figures). Any value needing more
  crosses the wire as a **string** (uids, versions, epoch/shared times). Absolute
  time never enters an engine: the synced clock lives in Python; engines only ever
  receive small relative values (`/cue <cueId> <sharedTime-as-string>` is converted
  by helper to a local relative delay before the engine sees it).
- Pi Zero 2 W is the constrained reference target; PD is single-threaded — no
  per-frame framework traffic on the engine's socket.

## 13. Migration (deployed fleets: Kite Choir, The Plants)

- **Zero port changes. No reflash. No flag day.**
- `uid == MAC` on Pis, so heartbeat correlation carries over.
- Transition aliases, kept exactly one release then deleted: `/helper/*` → `/os/*`;
  bare `/gain` (and `gain2`/`backing`/`echo`) → `/p/*`; old samplepacks path →
  symlink to the assets root.
- `bopos.devices` keeps working as the seed. A patch without a manifest still gets
  the legacy sliders.

## 14. Rejected by design (do not reintroduce without a contract revision)

Port consolidation and renumbering; a capability broadcast/registry (pull via
`/os/report` + manifest instead); runtime parameter introspection or
params-announce protocols; telemetry/log streaming (heartbeat absence is the
alarm); envelope-carrying cues (crossfades are dashboard param automation);
a separate hello/handshake family (the fast heartbeat is discovery); per-device
spatial gain broadcast at fleet scale; per-host branching in message semantics
(differences are declared facts, never special cases).
