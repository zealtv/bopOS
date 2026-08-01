# Ground truth — engine-boundary council, 2026-07-11

Verified facts about the current bopOS engine boundary, with sources. Where the
design brief and this file disagree, this file wins. Everything here was read
directly from the repository on 2026-07-11 (commit `0cd388a` on `main`).

## 0. Authority and constraints (ratified, not open for redesign)

- **OSC contract v1.1** (`docs/OSC-CONTRACT.md`) is ratified. The seam law (§1):
  bopOS *provides* named full-state terms, *owns* the machinery producing them,
  *enforces* only mute, and **never composes a provided term into a patch
  parameter**. Provided terms registry (§4.1): `master`, `point` (and `/cue` in
  spirit). §12: PD OSC floats are 32-bit — no >6-sig-fig values as floats,
  absolute time never enters an engine. §13: **zero port changes, no reflash,
  no flag day** for deployed fleets — but patches rewrite in lockstep (patch-
  facing wire compat is a non-goal). §14 rejected list includes telemetry/log
  streaming, runtime param introspection, port consolidation *without a
  contract revision*.
- This council designs; **Bob ratifies**. Agents never edit `.pd` files — PD
  changes must be specified as edit instructions, not implemented.
- 0-indexing is the wire/data-model default (CLAUDE.md, Bob 2026-07-11).
- Bob's pre-council rulings (`.notes/pd-engine-boundary-design-brief.md`,
  "Bob's rulings and taste"): **meters are not mission-critical — dropping
  them entirely is a valid solve**; the known real echo use is the
  capacitive-touch stream forwarded from `io/main.py` through PD back out to a
  PD dashboard via `/rpt` (messy; Bob suspects a **report-on-request model**);
  taste criterion: *simple, clean, understandable, performant* — prefer what a
  patch author can hold in their head over preserving every capability.

## 1. Process and port topology (as deployed)

Contract §4 table, verified against code:

| Port | Listener | Verified at |
|---|---|---|
| 5550 | dashboard (LAN, fleet→dash) | helper.py:290,331-332 sendto; pd/bopos.osc.pd lines 5-7 (`netsend -u -b` → `connect 255.255.255.255 5550`) |
| 6660 | PD `netreceive -u -b 6660` (bopos.osc.pd line 3) **and** helper.py's own LAN listener (helper.py:795-820, SO_REUSEADDR+SO_REUSEPORT) | both bind the same broadcast port on one device |
| 6661 | PD `netreceive -u -b 6661` (line 15); helper's OSCClient targets it (helper.py:43-44) | localhost, helper→engine |
| 6662 | PD `netreceive -u -b 6662` (line 88); io/main.py sends there (io/main.py:20,41) | localhost, io→engine |
| 7770 | helper.py `OSCServer(('',7770))` (helper.py:42); PD forwards `route helper` traffic there (bopos.osc.pd lines 21-24,28) | localhost, engine→helper |
| 8880 | io/main.py `OSCServer(('127.0.0.1',8880))` (io/main.py:19,219); PD forwards `r to-bopos-io` traffic there (lines 83-87,126) | localhost, engine→io |

So on one production device **two processes independently listen on LAN 6660**
(PD and helper), each routing the subset it owns. helper's heartbeat goes
directly to 5550, not through PD (helper.py:325-336) — engine death ≠ device
death.

## 2. What `pd/bopos.osc.pd` actually does (309 lines, read in full)

Ingress:
- **6660 → oscparse → `route all` → `route-by-id`** (numeric `route -1` keyed
  on the `ID` global) → **`route p`** (strips the `p` selector) → `s osc-in`.
  Selector routing lives *in PD*; the `route-by-id` subpatch converts the first
  element to a symbol and routes on the current ID.
- **6661 (from helper) → oscparse → list trim → `route id identify pt cue`**:
  `id`→`s ID`; `identify`→`identify` message →`s bopos-notify`;
  `pt`→`s bopos-points`; `cue`→`s bopos-cue`; **anything else** → `list
  prepend from-helper` → `s osc-out` (i.e. echoed to the LAN as a report, and
  `print received osc from helper.py`).
- **6662 (from io) → oscparse → list trim → `s from-bopos-io`**.
- **Audition-only local port**: `r BOPOS_ENGINE_PORT` → `listen $1` →
  `netreceive -u -b` → oscparse → `route p id identify pt cue` → the same
  buses (lines 225-238). Set via PD's `-send` startup message by
  `tools/audition.py` (audition.py:111-118).

Egress:
- **`s osc-out` → `list prepend 0` → `babs.gate` → `list trim` →
  `oscformat rpt` → netsend 5550**: everything a patch (or the fallthrough
  above) sends to `osc-out` leaves the device as a broadcast **`/rpt …`** on
  5550. This is the legacy report/echo path.
- **`r osc-in` → `route echo`** — incoming `echo …` commands feed the same
  report path (the "echo functionality" Bob calls cruft).
- **`r osc-in` → `route helper` → `pd process-helper-messages` → netsend
  127.0.0.1:7770**: PD receives lifecycle/provisioning verbs on the LAN, then
  *forwards them back* to helper. The subpatch routes
  `patch addpatch checkout` (each with a 500 ms `pipe` delay and a
  `s bopos-notify` symbol) and `config reboot shutdown restart-engine update
  getsamples pullpatch`, re-formats with `oscformat`, → 7770. This is the
  "PD-to-helper boundary smell" in the brain dump.
- **`r to-bopos-io` → `pd process-io-messages` → netsend 127.0.0.1:8880**:
  patch-side IO verbs (`report create poll`, plus `/<name>/<cmd>` peripheral
  control) formatted and forwarded to io/main.py.

Globals / buses currently in the patch: `osc-in`, `osc-out`, `ID`, `RANDOM`,
`STARTDATE`, `STARTTIME`, `ACTIVEPATCH`, `PX`, `PY` (dev prints only),
`bopos-notify`, `bopos-points`, `bopos-cue`, `to-bopos-io`, `from-bopos-io`,
`BOPOS_ENGINE_PORT`. `RANDOM/STARTDATE/STARTTIME/ACTIVEPATCH/ASSETS` arrive via
the shell `-send` startup message (bash/start-engine.sh:91), not from helper.
`ID` is set two ways: `route id` off `osc-in` (LAN `id …`) and the 6661 `id`
route (helper's `/id` reply to `/config`).

## 3. What `pd/bopos.out~.pd` and friends do

- `bopos.out~` (70 lines): two `inlet~`; `r osc-in → route os → route master`
  → clip 0-1 → `$1 10` → `line~` → per-channel `*~` (10 ms master ramp,
  loadbang default 1); same pattern for `route mute` inverted (`1-$f1`);
  `r bopos-notify` → bang → 300 ms decay envelope on a 600 Hz `osc~` →
  `s~ $0-notify`, mixed into both channels **after master, before mute**;
  → `dac~`. Note: it listens for `os master` / `os mute` **on the `osc-in`
  bus**, i.e. it relies on PD's LAN routing spelling, not on the 6661
  helper-relay spelling (`/os/master` arrives at non-PD engines on 6661;
  PD's own path delivers `os master …` via osc-in after selector strip).
  There is **no level meter** in the current bopos.out~; the meter Bob
  mentioned emits `level <value>` from patch-side code to `osc-out`
  (audition-1b results).
- `bopos.point.pd`: `r bopos-points → route $1 → route $2 → outlet` — a
  point/element-scoped receiver abstraction.
- `bopos.feedback.pd`: legacy audible-feedback sequencer voice with
  `r reboot`, `r shutdown`, `r update`, `r aloha`, `r click` receives and its
  own `dac~` — pre-`bopos-notify` machinery, partially superseded (the brain
  dump: Bob moved notify tones into `bopos.out~`).

## 4. What `python/helper.py` actually does (1070 lines, read in full)

- **Two ingress surfaces**: the LAN 6660 listener thread
  (`handle_lan_datagram`, helper.py:631-792) speaking contract v1.1, and the
  legacy 7770 `OSCServer` with selector-free handlers `/config /update
  /getsamples /shutdown /reboot /checkout /patch /addpatch /pullpatch
  /restart-engine /store /load` (helper.py:1048-1059) — **7770 is what PD's
  forward targets**. The 6660 `/os/*` verbs delegate to the same callbacks
  (LIFECYCLE_VERBS/PROVISION_VERBS, helper.py:1013-1025), so lifecycle verbs
  are handled on *both* paths.
- **Engine delivery channel**: one `OSCClient` connected to 127.0.0.1:6661
  (helper.py:42-44). Delivered today: `/id` (config reply + assign), `/pt
  <pointId> <element> <v>` (point decomposition via `python/pointfield.py`,
  helper.py:545-584), `/cue <cueId>` at the local deadline (helper.py:1028-
  1036), `/load <key> <values…>`, `/identify`, and legacy bare
  `/update /shutdown /reboot /checkout /patch /addpatch /restart-engine`
  echoes of admin verbs.
- **Non-PD relay (seam-5)**: if `expected_engine_name() != "pd"`, helper
  selector-matches and relays `/os/master` and `/p/<name>` selector-stripped
  on 6661 (helper.py:645-650). Rationale: **SuperCollider 3.13 cannot join
  the already-bound 6660 socket** (verified, seam-5 results). PD keeps its
  direct 6660 path and gets no duplicate.
- **Engine detection**: `expected_engine_name()` = `run/engine.name` file →
  manifest `engine` → `"pd"` (helper.py:212-225).
- **Meters**: `meter_loop` (helper.py:354-383) broadcasts framework meter
  sources (`rssi`, `cpu_temp`) as `/<id>/p/<name>` to 5550 every
  `METER_INTERVAL` (min 1 s), gated by `bopos.config` `METERS` (default
  empty — off).
- **Mute**: amixer candidate walk, engine-stop fallback (helper.py:416-435).
- **Sync**: `/sync/ping`→pong (monotonic ns strings), `/<id>/sync/offset`
  slewed in `sync_node.py`; cue scheduling fires the bare `/cue` locally.

## 5. What `python/io/main.py` actually does (264 lines, read in full)

- Listens 8880, sends to PD on 6662 (io/main.py:19-20). Poll loop reads all
  registered peripherals at `poll_rate` (default **10 Hz**) and sends one OSC
  **bundle** of `/<name> <values…>` messages per tick (io/main.py:79-117).
- Command namespaces on 8880: `/io/create|poll|report|scan` (with
  `/io/error <name> no-bus`), `/system/rssi|id|ip|uptime|rev|patch|info`
  (device facts replied on their own addresses — overlaps helper's
  `/os/report`), `/<peripheral>/<command>` writes.
- Peripheral types: ADCs, accelerometer, **mpr121 12-channel capacitive
  touch**, OLED, switch — the touch stream is the known real `/rpt` debugging
  use (Bob).

## 6. The audition rig and macOS facts (tied evidence)

- **audition-0 port spike**: Linux delivers one broadcast to every
  SO_REUSEADDR listener (stock PD included). **macOS stock PD 0.55.2 cannot
  share 6660** (`Address already in use (48)`); Python needs
  SO_REUSEADDR+SO_REUSEPORT there. Shared-port *unicast* reaches exactly one
  process on both platforms. Verdict: audition needs a relay owning 6660,
  fanning out to per-instance localhost ports.
- **audition-1a**: `tools/audition.py` (265 lines, read in full) owns LAN
  6660, spawns N engines with per-node `BOPOS_ENGINE_PORT` (base 16661),
  heartbeats N virtual identities to 5550, and relays **only**
  selector-stripped `/p/<name>`, `/os/master`, `/os/mute`, and
  `/os/identify→/identify` to each node's local port (audition.py:149-170).
  Assignment/sync/points/cues are deliberately rejected. `/id` catch-up is
  launcher-owned.
- **audition-1b (three real PDs on the Mac)**: works via `BOPOS_ENGINE_PORT`
  ports 17661-17663; **each audition PD still attempts the fixed
  6660/6661/6662 binds** and logs errno 48 warnings; **PD's report netsend to
  `255.255.255.255:5550` fails on macOS with errno 49** ("Can't assign
  requested address") even though the patch-side meter correctly emits
  `level <value>` locally. macOS is the likely installation/performance
  platform (Bob 2026-07-08).

## 7. The SC starter (`templates/supercollider-bopos/`, read in full)

- `main.scd`: one sclang, one scsynth; `OSCdef`s on **recvPort 6661** for
  `/id`, `/os/master`, `/p/<name>`, `/pt <point> <element> <v>`, `/cue`;
  lazy per-element Synths (0-based → output channel); `boposOut` tail Synth
  is the sole final mix stage (smoothed raw master; framework never composes);
  asks helper `/config` on 7770 after binding. The README documents the
  selector-stripped 6661 surface as the engine seam for non-PD engines.
- Note the asymmetry: SC receives `/os/master` on 6661; PD receives
  `os master` via its own 6660 selector routing on the `osc-in` bus. Same
  term, two spellings/paths, per engine.

## 8. Traffic bounds (adjudicated or measured)

- `/pt` frame form, 5 points @ 30 Hz ≈ 3-4 KB/s broadcast, O(1) in fleet size
  (seam council judgment, adjudication #8).
- io poll default 10 Hz × one bundle; a 12-channel mpr121 ≈ 10 msg/s of ~12
  ints on localhost 6662 — cheap locally, expensive if echoed to LAN 5550 via
  `/rpt` (which is exactly the plant-installation debug pattern).
- helper meters: ≥1 s interval, off by default. Heartbeats: 10 s (2 s
  unassigned). PD patch meter `level` emission rate is patch-defined and
  currently unthrottled by the framework.

## 9. Known smells the council exists to rule on (from the brain dump, all verified present)

1. PD receives LAN admin verbs and forwards them back to helper on 7770
   (bopos.osc.pd `route helper` → process-helper-messages).
2. Selector/ID routing machinery lives inside PD (`route-by-id`, `s ID`,
   `route id` off osc-in) though identity feels like framework state.
3. Startup context (RANDOM/STARTDATE/STARTTIME/ACTIVEPATCH/ASSETS) arrives
   from the shell `-send`, not from helper; helper separately delivers `/id`.
4. `osc-in`/`osc-out` are vague bus names beside the newer `bopos-notify`,
   `bopos-cue`, `bopos-points`, `to-bopos-io`/`from-bopos-io` vocabulary.
5. The `/rpt` echo path broadcasts anything on `osc-out` to LAN 5550;
   `route echo` re-broadcasts incoming traffic; `PX`/`PY` prints are dev
   cruft; the 6661 fallthrough also feeds `/rpt`.
6. Meters: no framework definition of what a PD-side meter is; the one that
   exists (`level` → `/rpt`) rides the broken-on-macOS broadcast netsend.
7. Every PD instance binds three fixed ports (6660/6661/6662) even when
   launched as an audition instance with its own `BOPOS_ENGINE_PORT`.
8. `helper.py`'s name and its two overlapping ingress surfaces (7770 legacy
   selector-free vs 6660 contract) predate the contract; `io/main.py`'s
   `/system/*` facts overlap helper's `/os/report`.
