# Survey: dashboard device-identity and state model (subagent, 2026-07-13)

Facts gathered read-only by a Sonnet subagent; file:line verified at survey
time.

## 1. installation.json schema

- Top-level (`dashboard/installation.json:1-32`; `InstallationState.durable()`
  `dashboard/state.py:105-118`): `name`, `room` `{width, depth, units}`,
  `master`, `presets`, `facilitator_commands`, `listener` `{x,y,heading}`,
  `devices`.
- **`devices` keyed by `uid`** (opaque; uid == MAC on Pis) — `state.py:54,66-74`.
- Durable per-device: `DURABLE = ("id","name","pos1","pos2","patch")`
  (`state.py:8`) + `params` (`state.py:108-109`). `id` int, -1 = unassigned.
- Runtime-only (rebuilt each load, `_runtime_device` `state.py:59-74`): uid,
  online, last_seen, ip, version, engine_alive, rssi, report, declared,
  undeclared, rev, sync.
- `points` runtime-only, never in `durable()` (`state.py:24`); `muted`
  in-memory only, **not persisted** (`server.py:206`).
- Save: atomic tmp+replace (`state.py:182-189`), 1s debounce.
- **Device removal: NOT FOUND** — no del/pop on devices anywhere in
  state.py/server.py/osc_bridge.py; no ws message to forget. Every uid ever
  seen persists forever. Offline = `offline_sweep` 30s (`server.py:86-93`).
- Seed import: `--devices-file` CSV populates once if devices empty
  (`state.py:29-30,76-95`).
- Venues: `installations/<name>.json` = same durable shape
  (`state.py:203-256`). `load_venue` carries live runtime fields over by uid,
  replaces state wholesale, saves, and re-sends `/os/assign` to every
  assigned device (`server.py:312-322`). Venues never include points/muted.

## 2. Discovery / assignment

- Contract §2: `uid` = stable opaque key, primary-interface MAC → per-boot
  UUID fallback. §5 (`docs/OSC-CONTRACT.md:266-298`):
  `/all/os/assign <uid> <id> <name> [x y]×N` — idempotent full-state;
  element positions ride it, pair order = element index, 0-based; the node
  applies it, **sets its hostname**, tells the engine its id, acks by
  heartbeating the new id. Node persists assignment; dashboard keeps the
  uid→assignment table. Boot: local persisted → `bopos.devices` seed →
  unassigned (`id=-1`, never silent). Unassigned heartbeat ~2s, assigned 10s.
- §6 heartbeat: `/hb <uid> <id> <version> <engine-alive 0|1> [rssi]`.
- Flow: `/hb` → `osc_bridge.py:259-296` → `state.ensure(uid)`
  (`state.py:97-100`, id=-1). Bridge replays `/os/assign` on id mismatch or
  reconnect (rate-limited 2s, `osc_bridge.py:264-288`); params catch-up
  request on first-seen assigned (`osc_bridge.py:293-296`).
- UI assign: ws `assign_device {uid,id,name}` → `server.py:279-305`
  (validates id non-negative + not taken) → `OSCBridge.assign()`
  (`osc_bridge.py:217-225`) broadcasts `/all/os/assign`.
- **Hostname: NOT on the wire.** Not in `/hb`, not in `/os/report`'s tracked
  JSON (contract §6 report fields), not in `_runtime_device`. The node sets
  its hostname when applying assignment (§5 side effect) but never reports
  one. → ui-0's "suggest name from hostname" needs a wire addition.

## 3. Positions and elements

- `pos1`/`pos2` are the only two element slots — hardcoded two, not true N
  (`state.py:8,68`; `device_elements` `server.py:335-339` drops None slots,
  so pos2-only sends as element 0).
- ws `set_position {uid, pos1?, pos2?}` (`server.py:209-227`) stores, saves,
  re-sends full `/os/assign` if assigned ("positions ride /os/assign so the
  node persists them too").
- Dashboard ships point geometry (`/pt <n> <id x y r f>×n`) and element
  positions; the **node** computes per-element proximity (contract §4.1).
  `dashboard/points.py` validates geometry only.
- Positions can't be set for an unknown uid (`server.py:210-212`); positions
  persist forever with the device entry (no deletion path).

## 4. Listener puck

- `installation.data["listener"] {x,y,heading}` — **durable**, persisted
  (`state.py:23,111-118`); defaults room-center (`state.py:120-124`),
  clamped by `clean_listener` (`state.py:126-145`).
- ws `set_listener` → store, save, `send_audition_listener()`, broadcast
  (`server.py:228-235`).
- `send_audition_listener()` (`osc_bridge.py:123-137`) sends
  `/audition/listener <x> <y> <heading> <range>` **loopback-only**
  (127.0.0.1) for `tools/audition.py`'s preview mix — deliberately outside
  the ratified fleet contract (preview-3 results: "No listener term was
  added to the fleet OSC contract").
- Renders unconditionally on the map (`spatial.js` render; heading numeric
  input `dashboard.js:16,58,65-70`). Catch-up on `/audition/ready` replay
  (`osc_bridge.py:240-258`) and on ws state push (`server.py:98-101`).

## 5. Sidebar rendering

- `render()`/`row()` `dashboard.js:51-64`: assigned = id>=0 sorted by id;
  unassigned = insertion (first-heartbeat) order; separate DOM containers.
- Row: status dot (online / crashed [engine_alive==0] / offline), name-or-uid,
  "ID N · version", optional rssi.
- Liveness binary: online flips false after 30s silence (`server.py:86-93`,
  `device_offline` ws event). No stale tier.
- "Expected but absent": NOT FOUND as a concept — never-deleted entries with
  `online:false` passively serve that role; no badge beyond the offline dot.
