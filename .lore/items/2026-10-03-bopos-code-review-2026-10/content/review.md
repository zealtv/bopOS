# bopOS broad code review — 2026-10-03

Reviewed at commit `0c1388d` (main). Reviewer: Claude (Opus 5.5) in a Claude
Code session with Bob.

## Method

- Ran `tools/run-tests.sh fast` and `browser` from `~/.venvs/bopos`.
- Static checks: `pyflakes` and `vulture` over `dashboard/`, `python/`,
  `python/io/`, `tools/`.
- Function-size census (AST) across all Python.
- Diffed the websocket verbs the server handles against those the frontend
  sends.
- Read in full: `python/bopos.py`, `python/io/main.py`, `dashboard/state.py`,
  `dashboard/osc_bridge.py`, `dashboard/show_engine.py`, the `handle_ws`
  section of `dashboard/server.py`, the core `bash/` lifecycle scripts.
- Spot-checked: frontend JS (escaping, density), io peripheral modules,
  `python/fetcher.py` path guards, docs for references to missing files.
- **Not reviewed in depth:** `show_model.py`, preset code (being removed, loom
  `65`), `manifest.py`, `paramgen.py`, `identity.py`, frontend modules
  (`control-surface.js`, `spatial.js`, `monitor.js`), CSS, install scripts and
  systemd units.

## Size

~51k lines of Python/JS/shell/CSS/HTML outside the dotdirs and `pd/bop`;
roughly half is tests. Largest files: `dashboard/server.py` 3,321;
`python/bopos.py` 2,159; `dashboard/static/js/show.js` 1,784;
`dashboard/static/js/dashboard.js` 1,777; `dashboard/osc_bridge.py` 1,764.

## Test health

- **Fast tier:** 363 tests, ~3 s, all pass.
- **Browser tier:** 19 of 24 journeys pass. Five fail every run:
  `verify_control_column_scroll`, `verify_control_surface_component`,
  `verify_control_tab`, `verify_manifest_param_visibility`,
  `verify_preset_control_surface`. `verify_manifest_param_visibility` fails
  identically at `5506439~1` (before 2026-09-03), so the tier has been red for
  weeks unnoticed. One failure looks like a real UI bug: *"standalone
  facilitator shows only flagged parameters — ['gain', 'gain']"* (Remote
  renders `gain` twice). The others are timeouts waiting on Control-tab
  elements — plausibly tests that drifted from the UI.
- There is no CI; nothing runs either tier automatically.

## Bugs (most serious first)

### B1. One bad reference in `installation.json` wipes the installation — confirmed

`InstallationState._load` (`dashboard/state.py`) validates all-or-nothing: if
any seat references a group that doesn't exist (or any other field fails its
cleaner), `_load_invalid` is set and the dashboard starts from empty defaults
with no operator notice. `save()` has no guard on `_load_invalid`, so the next
ordinary save — `save_debounced()` after a master-fader move, a device alias
allocation on first heartbeat — overwrites the real file.

Reproduction (run in the session):

```python
json.dump({"schema":1,"name":"Kite Choir","seats":{"0":{"id":0,"name":"Spool 00",
  "positions":[],"params":{},"groups":[7],"bound":None}},"groups":{}}, open(p,"w"))
s = state.InstallationState(p)      # seats: {}, _load_invalid: True
s.data["master"] = 0.5; s.save()
# file now: name "bopOS", seats {}
```

### B2. `addpatch` deletes the existing patch before cloning

`add_patch_callback` (`python/bopos.py:1883`) `rmtree`s the destination, then
`git clone`s. A failed or timed-out clone leaves no patch — including the
active one, which then fails to launch. (Ruled moot by removing the Git route,
below.)

### B3. "Device disabled" can report success while still playing — likely, rig check needed

`set_device_enabled` (`python/bopos.py:604`) persists `device_enabled` and
updates node state *before* `enforce_mute`. If no mixer control works, it
returns without a receipt (deliberate; tested in
`test_failed_enforcement_emits_no_receipt`), but state stays changed. The next
`/os/report` carries `device_enabled: false, output_enabled: false` derived from
intent, and the dashboard's `enabled_status` becomes `current`. HiFiBerry
boards have no hardware mixer (`glean:test-rig`), so Ciro Toast is a likely
real case: the UI says disabled while audio plays.

### B4. LIS3DH module ignores the I2C address

`python/io/io_lis3dh.py` ignores `address` and constructs `PiicoDev_LIS3DH()`
at its default; it sets no `self.address`. So a create at the wrong address
silently "succeeds", and `/io/scan`'s `skip` set (built from `p.address`)
misses it — the scan probes a live LIS3DH, the contention the design forbids.
All other modules honour the address.

### B5. Io bridge error paths and thread safety

In `python/io/main.py`:

- `/io/create` with a malformed address (`int(args[2], 16)`) and `/io/poll`
  with a non-number raise inside the handler thread; no `/io/error` reply.
- Unknown `/io` verbs only print (also loom `60-io-dispatch-silence`).
- Re-creating an existing name replaces the instance without calling the old
  one's `cleanup()`.
- `write_data` (OSC server thread) and `read_data` (poll loop) touch the same
  chip with no lock.

### B6. Reported contract version is stale

`"contract_version": "1.16"` is hard-coded in `python/bopos.py`,
`tools/simfleet.py` and `tools/audition.py`; `docs/OSC-CONTRACT.md` is v1.17.

### B7. Browser tier red

See *Test health*.

## Complexity hotspots

- **`Dashboard.handle_ws`** (`dashboard/server.py:356`) — 1,093 lines, 89
  `elif kind ==` branches, plus lock re-entry via recursive self-calls.
- **`OSCBridge.handle`** (`dashboard/osc_bridge.py:1109`) — 546 lines, one
  function per inbound address family.
- **Three node implementations.** `python/bopos.py` (real node),
  `tools/simfleet.py` (N fake nodes) and `tools/audition.py` (laptop relay) each
  implement uid-admin dispatch, reports and provisioning verbs. Drift evidence:
  stale `contract_version` in all three; simfleet doesn't model manifest
  validation (loom `58/4`); simfleet's docstring still describes
  `LegacyProtocol` and `bopos.osc.pd`.
- **A second patch-distribution route via Git.** `addpatch` / `pullpatch`, a
  `git pull` inside `switch_patch_callback`, `bash/pull_active_patch.sh` (which
  also forces a full reboot), the dashboard's "Pull latest" button, the `git`
  field in `/os/patches`, and git-managed skips in distribution and fetch. This
  contradicts "patches reach devices only by push".
- **Defensive code that can't fire.** `send_to_engine` swallows every send
  error and returns a bool, yet ~10 callers wrap it in try/except
  (`apply_assign`, `apply_unassign`, `apply_points`, `relay_provided_term`,
  `fire_event_to_engine`, `load_callback`, `add_patch_callback`, …).
- **Duplicated cache warming.** `_asset_warm_loop`/`warm_asset_cache`/
  `initialise_asset_cache` and the `patch` trio are copies.
- **Dense frontend.** `dashboard.js` has 74 lines over 200 characters; the
  longest (`patchDiagnostics`, line ~1155) are ~1,500-character template
  literals.
- **Pinning.** `device_operations` / `device_generations`, per-device
  `desired_patch` overrides, `patch_pinned` projection — slated to go with loom
  `66-projects`.

## Dead or stale code

- **Websocket verbs handled but never sent by the UI:** `add_patch`,
  `switch_patch`, `sync_distribution`, `set_points`, `list_venues`,
  `save_show_as`, `restart_edit` (alias of `relaunch_edit`); `set_param` is
  exercised only by tests.
- **Unused methods:** `server.py` `active_param_identities`,
  `_current_patch_fingerprint`, `device_elements` (also lacks `self`);
  `simfleet.py` `wire_id`, `match_id`, `admin_request`.
- **Superseded scripts:** `bash/update.sh`, `bash/checkout.sh` — replaced by
  `converge_framework` in `bopos.py`; only a hint in `provision.sh` names them.
- **Leftovers:** `add_seat`/`update_seat` still pass a per-seat `patch` that
  `clean_seat` drops; `set_editor_point_element` allows only elements 0/1;
  `pull_active_patch.sh` hard-codes `/home/pi/bopOS`; redundant conditional in
  the `/os/fetch` short-args branch.
- **pyflakes:** unused `json` import (`server.py`), unused
  `patch_manifest` import (`show_model.py`), `identity` shadowed by loop
  variables (`server.py:1831`, `2067`), unused `socket` import and
  placeholder-less f-strings (`io/main.py`), unused `global` (`nodelog.py`),
  unused `HEIGHT` import (`io_ssd1306.py`).
- **Docs:** `docs/OSC-CONTRACT.md`, `docs/OSC-REFERENCE.md`,
  `docs/COMPOSING.md` cite `pd/bopos.pd`; the file is `pd/bopos~.pd`.

## Scaling concerns (measure before a large fleet)

- **Clock-sync traffic.** The dashboard broadcasts `/sync/ping` at ~2 Hz;
  every assigned node unicasts a pong; for every pong the dashboard sends
  `/<id>/sync/offset` to the execution target, which defaults to
  `255.255.255.255`. At Kite Choir's 52 positions that is ~100 broadcast
  datagrams/s that every node receives and discards, on Wi-Fi broadcast's
  basic-rate airtime.
- **Monitor console tap.** `OSCBridge._send_to` and `handle` broadcast every
  OSC message in and out (`osc_out` / `osc_in`) to every connected browser,
  each via its own asyncio task; filtering is client-side. Heartbeats, pongs,
  offsets and 25 Hz `/pt` frames all go to every tab.

## Also noted

- **No CI** — the browser tier's rot went unnoticed for weeks.
- **LAN trust model.** Any host on the installation network can reboot, update,
  switch patches, write `/os/store` keys, or make a node fetch from an arbitrary
  URI. Fine on a private network; worth a deliberate decision before shows on
  shared or public Wi-Fi.
- **Two OSC libraries.** Nodes use `pyOSC3` (48 files import it); the
  dashboard and tools use `python-osc` (58).
- **Unpinned dependencies** in `dashboard/requirements.txt`.
- `python/fetcher.py` path guards (absolute paths, `..`, realpath/commonpath
  containment) look sound.
- **Done well:** atomic saves with rollback, fail-closed input cleaning,
  comments that explain why, a fast suite that runs in seconds.

## Bob's rulings (2026-10-03)

- Put every finding on the loom as stitches; every complexity point gets
  addressed.
- **Remove the Git patch route** for now (moots B2).
- A stitch to assess clock-sync messaging and find a design that keeps sync
  while reducing traffic.
- A better networking design for the Monitor.
- Keep this review in lore.
