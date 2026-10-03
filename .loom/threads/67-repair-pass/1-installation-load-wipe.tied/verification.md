# Installation load preservation

## Decision and behavior

An installation that fails its existing load/clean checks now stays protected
in place. `save()` raises an `OSError` before touching any directories or
temporary files, so existing transactional setters can roll back and report
failure. Debounced saves do not schedule writes in a failed-load session;
shutdown also respects the guard. Missing files still support a new
installation, but a dangling symlink is preserved as a failed load.

Dangling group references are rejected rather than silently dropped. There is
no evidence whether the membership or the group catalog is wrong, so keeping
the original topology avoids guessing. The notice directs the operator to
repair the original file and restart. No separate backup is required because
this session cannot overwrite the original. No Pd or wire changes were made.

Venue loading already validates topology before replacing current state or
adopting legacy group names. Rejected reads now add a deduplicated notice, and
saving over an existing unreadable/invalid venue checks it first and refuses.
A failed current installation also cannot be saved as an empty venue snapshot.
The backend broadcasts newly added notices on rejected venue operations.

The existing Show warning renderer now serves both a loaded Show and the
no-Show state; otherwise a startup failure's notice would never be visible.
Notices remain runtime-only and are escaped by the existing renderer.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python
  tests/test_state_load_safety.py`: nine checks passed, including multiple
  invalid-document subcases; see `focused.log`.
- `./tools/run-tests.sh fast`: all 377 tests passed; see `fast.log`.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python
  tests/verify_state_load_safety.py`: ten browser checks passed in the full
  tier (nine in the first focused run). The real
  dashboard rejected startup state, preserved bytes past the debounce
  deadline and on shutdown, retained the notice after reconnect, refused
  overwriting an invalid venue, and cleared the startup lock/notice after
  repair and restart, then successfully persisted an ordinary master change.
- `./tools/run-tests.sh browser`: 25 journeys attempted, 20 passed and five
  failed; status 1. The failures match the existing baseline exactly:
  `verify_control_column_scroll.py`, `verify_control_surface_component.py`,
  `verify_control_tab.py`, `verify_manifest_param_visibility.py`, and
  `verify_preset_control_surface.py`. Complete results are in `browser.log`.
- `node --check dashboard/static/js/show.js`: passed.
- Touched Python files compile using `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache`.
- `git diff --check`: passed.
- Stitch `verify.py` reruns the focused state checks and JS syntax check from
  either the claimed or tied stitch path; passed.

The browser journey required unsandboxed Chromium and loopback ports; its
initial sandboxed launch was blocked. All fixtures use temporary state,
patch and asset directories. No installation LAN, Pis, audio, Pd or iPad
checks were run. The known red browser journeys remain owned by
`5-browser-tier-red`.
