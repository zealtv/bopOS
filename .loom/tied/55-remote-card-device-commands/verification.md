# Verification

Verified on 2026-08-03.

- `./tools/run-tests.sh fast`: 298 tests passed.
- `python -m unittest tests.test_remote_live_bar`: 4 tests passed.
- `python -m unittest tests.test_remote_verb_promotion`: 9 tests passed.
- `python -m unittest tests.test_device_control_routing`: 6 tests passed.
- `python -m unittest tests.test_css_component_ownership`: 5 tests passed.
- JavaScript syntax checks passed for `facilitator.js` and
  `control-column.js`.
- Relevant Python files compiled successfully.
- `git diff --check` passed.

The browser journey could not start in this sandbox: Chromium failed during
launch when its Mach-port rendezvous bootstrap was denied. It failed before
the dashboard loaded, so no visual/browser result is claimed. Static journey
expectations were updated to assert commands and selectors on every All,
group, and Seat card.
