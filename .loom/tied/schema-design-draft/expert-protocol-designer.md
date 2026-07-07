# bopOS OSC contract — the protocol-designer's cut

## 1. Lens & altitude

My seat is OSC grammar and wire hygiene, so I zoom **all the way in**: actual
address strings, actual type tags, actual arg order, the declaration mechanism,
and the port layout. A contract is only "first-class" if I can read a stray
packet in a 2am dashboard log and know exactly who sent it, what it means, and
what a correct reply looks like — without grepping code. Everything below is
graded against that test. Where the mandate asks for options (E), I give two and
pick; elsewhere I make the call.

## 2. Problem reframing

bopOS has a *working* protocol that grew organically and now has three
protocol-craft defects, independent of any feature:

1. **No address grammar.** `/hb`, `/1/gain`, `/1/helper/update`, `/io/create`,
   `/system/rssi` follow no shared rule. You can't predict an address; you
   memorize it.
2. **Conflated planes.** Framework admin (`/helper/*`), patch output (`/gain`),
   offboard IO (`/io/*`), and device facts (`/system/*`) share one flat space
   with no marker saying which is which — so the dashboard hardcodes three
   sliders it should have discovered.
3. **Broken request/reply symmetry and identity.** `/hb` carries no identity;
   `/echo` is a reflection hack standing in for a real probe; discovery is
   ad-hoc.

The fix is not new machinery. It is **one addressing rule, a small set of named
planes, and request/reply symmetry** — then the feature families (sync, cue,
spatial, distribution) drop into that grammar for free.

## 3. Proposed design

### 3.1 The one grammar rule

Every LAN message is:

```
/<selector>/<plane>/<member>   ,typetags   args…      (dashboard → device)
/<plane>/<member>              ,typetags   args…      (device → dashboard)
```

- **selector** ∈ `all` | `<id>` (numeric). Devices route on it exactly as
  today (`route-by-id`, `/all` = everyone). Device→dashboard messages omit the
  selector — the **source identifies the sender**, so the reply address equals
  the request member. That symmetry is the whole readability win.
- **plane** is the namespace root and the single most important token:

| plane | owner | meaning | broadcast/unicast |
|---|---|---|---|
| `/os/*`  | **framework** | identity, lifecycle, discovery, persistence, distribution | both |
| `/io/*`  | **framework** | offboard hardware IO (I2C/GPIO on the node's own bus) | unicast |
| `/sync/*`| **framework (Python)** | clock offset estimation | broadcast |
| `/cue/*` | **framework (Python)** | scheduled fires; PD only ever gets relative ms | both |
| `/point` | **framework/dashboard** | spatial mask input (moving point) | broadcast |
| `/p/*`   | **patch** | patch-declared parameters — the *only* place output semantics live | both |

Rule of thumb for the boundary: **`/os` `/io` `/sync` `/cue` `/point` are the
framework's closed vocabulary; `/p/*` is open and owned entirely by the patch.**
gain/gain2/backing/echo move under `/p/*` and stop being framework's problem.

### 3.2 Identity & assignment (A, C)

Identity primitive is a **`nodeid` string**, not a MAC. On a Pi it *may be* the
MAC; on a live-booted x86 box it's `/etc/machine-id` (or a persisted uuid). The
framework never assumes MAC, WiFi, or pre-registration — that is what makes an
x86 box first-class. `bopos.devices` becomes an *optional* pre-seed keyed on
nodeid, not a gate; an unknown node is `id = -1` (unassigned), and stays alive
and discoverable.

```
/os/hb   ,sifs[f]  <nodeid> <id> <version> <engine> [<rssi>]   dev→dash, 5s
```

`version`/`engine` are **strings** (semver, `"pd"`/`"sc"`/`"of"`) — emitted by
Python, so no PD float limit. `rssi` present only if the node has WiFi
(switchable via `bopos.config`); its *absence* is how the dashboard learns a
wired x86 node has no signal metric — no separate capability packet needed. The
heartbeat comes from helper.py, so **engine death ≠ device death**.

Assignment reuses broadcast, no new selector:

```
/all/os/assign  ,siss[ffff]  <nodeid> <id> <name> [<posx> <posy> <pos2x> <pos2y>]
```

Each device checks `nodeid == me`; the winner applies id/name/position and
acks by heartbeating with the new id. This is dashboard-3's assign flow.

### 3.3 Discovery / liveness / debug (replaces `/echo`)

```
/all/os/ping  ,i <token>        →   /os/pong ,ii <token> <nodeid-hash>   (dev→dash)
/all/os/report                  →   /os/report ,s <json>                 (dev→dash)
/<id>/os/log  ,i <0|1>          (verbose mode toggle)  →  /os/log ,s <line>
```

`ping/pong` echoes the caller's token so round-trip latency is measurable per
device (the real job `/echo` was faking). `/os/report` returns a JSON blob
(engine, has_i2c, has_wifi, audio_channels, patch, uptime, git-rev,
contract-version). This is my answer to **G**: **no standalone capability
*broadcast*.** Capabilities are pulled on `/os/report` (cold, on demand) plus
the 2–3 live-changing fields folded into `/hb`. Concrete uses that justify even
this much: dashboard hides the RSSI column for wired nodes, hides I2C UI for
nodes without a bus, and labels PD-vs-SC engines. A push-broadcast of static
capabilities every 5s would be pure noise — rejected.

### 3.4 Patch parameter declaration/discovery (D) — the keystone

The patch ships a **manifest** `bopos.patch.json` in its repo root:

```json
{ "engine": "pd", "entrypoint": "main.pd",
  "params": [
    {"name":"gain",   "type":"f","min":0,"max":1,"default":0.75,"group":"mix"},
    {"name":"backing","type":"f","min":0,"max":1,"default":0.8, "group":"mix"},
    {"name":"echo",   "type":"i","min":0,"max":1,"default":0,   "group":"fx"} ] }
```

helper.py (engine-agnostic — it just reads the file) answers discovery:

```
/<id>/os/params            →   /os/params ,s <manifest-params-json>   dev→dash
```

The dashboard **renders sliders from the declaration** — names, ranges,
defaults, grouping — and never hardcodes a control again. Values then flow in
the patch plane:

```
/<id>/p/gain  ,f 0.5        /<id>/p/echo ,i 1        /all/p/gain ,f 0.3
```

PD routes `route p` → its own param space; an SC patch does the same on its
side. The manifest is the single source of truth for both "what starts this
patch" (entrypoint/engine — generalises `start.sh`) and "what can I control."

### 3.5 Sync / cue / spatial (reserved, shaped now)

```
/sync/beacon ,is <seq> <t_monotonic_as_string>     (leaderless fallback)
/cue ,is <cueId> <sharedTime_as_string>   →  helper converts to local delay,
        fires localhost  /cue ,s <cueId>  at the engine   (PD never sees time)
/point ,fff <x> <y> <radius>               (dashboard or video-mask layer emits)
```

64-bit times ride as **strings** (the Happy Brackets rule); PD only ever
receives small relative ms. `/point` is deliberately dumb geometry so the
"video-as-mask" idea is just another emitter of `/point` or `/p/*` — no new
family.

### 3.6 Distribution (H)

Generalise `getsamples` into a source- and media-agnostic fetch with a **named
landing contract**:

```
/<id>/os/fetch ,ss <source-uri> <slot>     →  /os/fetch ,si <slot> <0|1 ok>
```

`source-uri` dispatches on scheme (`gdrive:` `http:` `rsync:` `file:`), so
local-network push (dashboard as HTTP/rsync source) replaces cloud-only gdown.
The **landing location is one convention**: assets land under
`$BOPOS_ASSETS = patches/<active>/assets/<slot>/`, exported into the engine env
at launch. Any engine (PD/SC/oF) finds delivered media at the same predictable
path; `slot` lets a patch keep sample-set vs video vs model separate.

### 3.7 Persistence & IO

```
/<id>/os/store ,s… <key> <values…>    /<id>/os/load ,s <key>  →  /os/load ,s… <key> <values…>
```

**IO boundary (F):** `/io/*` owns what is *offboard and bus-addressed on the
node* (I2C/GPIO sensors, actuators) — engines do this badly, which is why it's
offboarded. Musical/native IO (MIDI, HID, audio-in) enters *through the engine*
and, if it must reach the dashboard, surfaces as `/p/*`. Sharp line: **bus
hardware on the node → `/io`; musical/control events the engine consumes
natively → engine, exposed as `/p`.**

## 4. How it fits today's system (E: ports + migration)

Namespace changes map cleanly onto the existing `route` in `bopos.osc.pd`:
`/helper/*`→`/os/*` (alias `/helper` one release), bare `/gain`→`/p/gain`
(alias one release), `/system/*`→`/os/report` fields, `/io/*` unchanged. The
localhost forwards (PD→helper 7770, PD→io 8880, replies 6661/6662) keep working;
only the address strings change.

**Ports — I reject "consolidate to one socket."** The current topology encodes a
*correct* separation: a LAN broadcast plane (5550 up / 6660 down) and a
localhost IPC plane (the 66xx/77xx/88xx block). That separation is good protocol
design; the "smell" is *undocumented arbitrary numbers*, not the socket count.

- **Option A — document + centralise (recommended).** Keep all six sockets;
  move every number into one `bopos.ports` config read by PD-launch and Python;
  write the rationale into `docs/OSC-CONTRACT.md`. **Migration cost: ~zero** (no
  wire change), and it kills the actual smell.
- **Option B — renumber into a legible block** (`50xx`: 5000 dev→dash, 5001
  dash→dev, 5010/5011 →engine, 5020/5021 engine→). Cost: one coordinated update
  wave — PD patch constants (Bob's domain) + Python; deployed fleets flip via
  the existing `/os/update` (git pull + reboot). During rollout the dashboard
  listens on **old+new** so a mixed fleet survives one release. Do this only if
  a reflash is already happening.
- **Rejected — single port, namespace-routed both ways.** Breaks the
  co-located dev/audition case (dashboard *and* engine instances on one laptop
  sharing one port), for a cosmetic gain. Not worth the risk.

My call: **A now, B opportunistically.** The grammar rename is the real fix; the
port count is fine.

## 5. Why it's elegant / right

- **Smallest vocabulary that works.** Six planes, one addressing rule. Every new
  feature (sync/cue/spatial/video-mask/distribution) is an *address inside an
  existing plane*, not a new concept — the vocabulary stops growing.
- **The framework/patch boundary is a *token*, not a convention.** `/os` `/io`
  `/sync` `/cue` `/point` are closed and framework-owned; `/p/*` is open and
  patch-owned. The framework "provides transport/orchestration, never output
  semantics" — enforced by grammar, not discipline. gain/echo living under `/p`
  is the boundary made visible on the wire.
- **Fail loud.** Selector, plane, member are all inspectable in a raw packet; an
  unknown plane is an obvious error, not a silent misroute.
- **Platform-agnostic by construction.** nodeid (not MAC), string version/engine,
  optional rssi, no pre-registration gate → a live-booted x86 box heartbeats and
  discovers on day one.

## 6. Tradeoffs, risks, not-solving

- Aliases (`/helper`, bare `/gain`) mean a transition release carries both
  spellings — accepted, one release only, then deleted.
- The manifest duplicates a little of what a patch already "knows"; worth it to
  free the dashboard from hardcoding. Risk: manifest drifts from the patch —
  mitigate by having the launcher validate params exist before start.
- I do **not** design the scene/sequencing *language*, video-mask *authoring*,
  or falloff DSP — those are patch/dashboard concerns that merely *emit* into
  `/p/*` and `/point`. I do not settle leader election for sync (defer to the
  clock-sync thread); I only reserve its grammar.
- 32-bit float risk is contained to one rule: **any value >6 sig figs crosses
  the wire as a string** (`version`, `engine`, all `*_as_string` times).

## 7. Smallest first step

Write `docs/OSC-CONTRACT.md` with the grammar rule, the six-plane table, and the
message shapes above — **and add the `bopos.patch.json` manifest to the
`default` patch with a `/os/params` reply in helper.py.** That one move proves
the framework/patch split end-to-end (dashboard renders sliders from a
declaration) without touching PD, ports, or deployed wire — everything else is
downstream of it.
