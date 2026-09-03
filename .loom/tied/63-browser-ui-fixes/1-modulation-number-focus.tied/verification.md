# Verification

## Passed

- `node --check dashboard/static/js/control-host.js`
- `node --check dashboard/static/js/facilitator.js`
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python tests/verify_interaction_guard.py`
  - Chromium: 13/13 focused checks passed.
  - Includes primary-click focus and typed-value survival across several live
    heartbeats on both desktop Control and Remote.
- `./tools/run-tests.sh fast`
  - 363 tests passed.

## Browser-tier boundary

`./tools/run-tests.sh browser` was run. The new focused interaction journey
passed standalone, but the full tier did not reach a clean result: the first
two adjacent journeys timed out in pre-existing setup/navigation assertions
(`verify_control_column_scroll.py` waiting for four fixture cards, and
`verify_control_surface_component.py` waiting for target `g0`). The first
failure reproduced standalone and occurs before either journey exercises the
changed pointer/focus behavior.

The focused journey was also invoked with
`BOPOS_PLAYWRIGHT_BROWSER=firefox`, but this machine does not have Playwright's
Firefox 1532 executable installed. No Firefox automated pass is claimed. The
reported Firefox behavior is addressed at the shared event-order cause, and
Chromium reproduces the original failure before the fix and passes after it.
