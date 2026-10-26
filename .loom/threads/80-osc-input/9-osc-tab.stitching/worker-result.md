READY FOR REVIEW

Phase B of 8/9: the OSC tab, built from the approved mockup with the manager's notes applied.

## What changed
- `dashboard/osc_input.py`: `reference()` builds commands, events, params and groups from the
  active manifest with the input's own ambiguity rule; `snapshot()` adds `host`, `target`
  and `reference`; `active_manifest()` is shared with `handle()`; `host()` uses `--public-url`
  else the outgoing-interface address (unsent UDP `connect()`, once).
- `dashboard/static/index.html`, `js/dashboard.js`: the **OSC** tab, last in the bar.
  The "eighth tab" comment on the Remote link follows.
- `dashboard/static/js/osc-reference.js`, `css/osc-reference.css`: renders `state.osc_input`.
  No new websocket type, so `SNAPSHOT_TYPES` is unchanged. Component CSS lives in its own file.
- `tests/verify_osc_tab.py`: new journey (see below).
- `tests/verify_control_tab.py`: the tablist guard counts seven tabs now.

## Manager notes
1. Clamp tag now uses `--dim`, not cyan; rejections keep the amber ⚠.
2. Newest-first, `<target>` placeholder, no per-row copy buttons (the one Copy for IP and
   port stays), outgoing-interface IP kept.
3. Journey covers: fleet-patch reference; Patch Edit regenerating it (and the "Generated from"
   line, then restoring on leaving); real UDP producing a rejection and a clamp live without
   reload; ambiguity flag (event+param clash, plus a clean row without it); groups by name and
   `g<id>`; no page errors; no horizontal scroll at 390 px.

## Verification
- `python tests/verify_osc_tab.py`: all 17 checks PASS.
- `./tools/run-tests.sh browser` (after `git merge main`, already up to date): 73 PASS, no FAIL.
  The first run failed `verify_control_tab.py` on its "exactly six tabs" guard, fixed above.
- Fast suite ran green in the commit hook (641 tests).

## Look hardest at
- `snapshot()` now loads the manifest from disk on every state broadcast, as `public_state`
  already does elsewhere; fine at current rates but it is extra I/O per broadcast.
- The phone tab bar scrolls sideways, so the OSC tab sits off-screen at 390 px (as Assets did).
- No `.pd` edits, no hardware.
