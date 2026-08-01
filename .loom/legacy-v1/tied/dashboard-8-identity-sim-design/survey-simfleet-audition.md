# Survey: simfleet & audition rig (subagent, 2026-07-13)

Facts gathered read-only by a Sonnet subagent; file:line verified at survey
time.

## 1. tools/simfleet.py

- CLI (`simfleet.py:681-720`): `--devices` (default 5), `--drop`,
  `--jitter-ms`, `--unresponsive`, `--unassigned`, `--wired`,
  `--engine-dead`, `--ephemeral`, `--state-dir`, `--devices-file`,
  `--hb-interval` (10s), `--boot-secs`, `--target` (255.255.255.255),
  `--report-port` (5550), `--cmd-port` (6660), `--manifest`,
  `--sync-skew-ms`, `--sync-jitter-ms`, `--version`.
- Identity synthesis (`simfleet.py:660-663`):
  `mac = 02:53:49:4d:<hi>:<lo>`, `hostname = sim<i>`, for i in 1..N — the
  source of the persisted `02:53:49:4d:*` rows. `--devices-file` CSV gives
  `(uid, name, id)` instead.
- Binds 6660 with SO_REUSEADDR/REUSEPORT (`simfleet.py:192-199`); sends to
  target:5550. Same LAN ports as real fleet.
- Assignment persistence: `state_dir/<mac-dashes>.json` `{id,name,positions}`
  written on `/os/assign` (`simfleet.py:145-176,502-517`), loaded at boot
  unless `--ephemeral` (boots id=-1). **No CLI for initial positions** —
  positions only arrive via `/os/assign` at runtime, like real devices.
- Simulates: hb, ping/pong, assign, identify, mute, master, params, fetch,
  admin verbs, report (`engine: pd`, audio_channels 2), probe, sync
  ping/offset, cue, /pt via shared `python/pointfield.py`
  (`simfleet.py:59-598`). Indistinguishable from a real Pi at protocol level.

## 2. Audition rig

- `tools/audition.py` (audition-1a): one process owns LAN 6660 (sole binder,
  v1.2 §4.2), relays selector-matched traffic to N real engines on localhost
  ports (`audition.py:73-88`). CLI keeps simfleet-compatible core flags so
  audible + protocol-only instances mix in one session
  (`.loom/tied/audition-1a-relay-launcher/instructions.md:9-11`).
- UIDs: `audition-<i:04d>` (`audition.py:79`), deliberately IP-independent.
  `--engine-port-base 16661`, `--id-base 1`, `--audio-backend
  coreaudio|jack|none`, `--no-engine`, etc. (`audition.py:369-389`).
- Audition nodes are **ordinary dashboard devices** — assigned by the same
  `/all/os/assign`; the relay retains true-N positions though the
  fixed-stereo preview consumes ≤2 (preview-1 instructions:10-19). No
  separate audition-position concept.
- Preview stack (all tied): preview-0 fixed-stereo matrix model
  (`python/audition_matrix.py`; 0 pos = bypass, 1 = constant-power pan,
  2 = dual mono; `/audition/matrix <l0> <l1> <r0> <r1>`); preview-1 relay
  integration (relay-local listener, loopback-only); preview-2 engine
  adapters (PD send bus + SC OSCdef); preview-3 dashboard puck
  (`/audition/listener` loopback-only, `/audition/ready` replay,
  `osc_bridge.py:123-137,241-258`).

## 3. Dashboard's view of sim vs real vs audition

- **No kind/origin/type field anywhere** in `dashboard/state.py` device
  records; `durable()` persists whatever heartbeated. Only origin-aware
  line in the dashboard: `osc_bridge.py:252` `uid.startswith("audition-")`
  — used solely to pick devices for assign-replay after relay restart.
- No allowlist/denylist by prefix or IP; `ensure(uid)` persists any
  well-formed `/hb` sender (`osc_bridge.py:259-289`, `state.py:97-100`).
  That's exactly how five `02:53:49:4d:*` + three `audition-*` + bop000
  accumulated. Rows keyed by uid, so many uids on one IP don't collapse
  (`_device_for_reply` IP fallback is reply-routing only,
  `osc_bridge.py:227-238`).

## 4. Launch orchestration

- `dashboard/README.md:6-47`: server.py in one terminal, simfleet in
  another; audition.py separately when audible preview wanted. **No
  combined launcher script exists** (bash/ has no simfleet/audition hits).
- Shared defaults: cmd 6660, report 5550, broadcast target.
- verify scripts launch server + simfleet on non-default ports (repo
  convention).

## 5. Contract constraints

- §4 (v1.2): bopos.py/relay is the **sole** LAN 6660 binder in production;
  engines localhost-only (6661 surface; audition instances get
  `BOPOS_ENGINE_PORT`, "only the port number moves",
  `docs/OSC-CONTRACT.md:172-174`).
- §5: uid is opaque and node-chosen — `sim1`-style and `audition-0001`
  uids are legitimate per spec. Ephemeral hosts re-assigned each boot
  (matches `--ephemeral`).
- §6: `/hb` is the sole discovery path — no registration message.
- Same-host coexistence of multiple 6660 binders rides SO_REUSEADDR (spike
  `audition-0-port-spike`, Linux-verified); **no explicit contract ruling**
  on sanctioned same-host multi-simulator use — only the production
  single-binder rule. NOT FOUND as a ruling.
