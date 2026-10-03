# Test gate implementation and verification

The versioned pre-commit hook runs the existing fast entry point and refuses
commits on any nonzero result, including unavailable Python. The idempotent
installer sets the clone's local `core.hooksPath` and refuses to overwrite
another hook configuration. Dashboard setup installs it and includes pyOSC3,
which the fast tests need. The hook is installed in the working clone.

GitHub Actions was selected over a laptop scheduler because a laptop can be
asleep/offline and its logs are not shared. Fast tests run on push/PR; browser
tests run independently on PR, daily at 17:23 UTC, and manual dispatch. Both
jobs run on scheduled/manual events. Chromium is installed with Linux system
dependencies; browser failure survives the `tee` pipeline, every verifier is
attempted, and the summary/log are retained even on failure. The workflow
does not waive existing browser failures.

## Commands and results

- `./tools/install-hooks.sh`: installed successfully; `git config --get
  core.hooksPath` reports `tools/hooks`.
- `./tools/run-tests.sh fast`: 368 tests passed; see `fast.log`.
- `tests/test_commit_gate.py` (part of fast): four real-Git checks cover a
  failing test refusing a commit, a corrected test allowing it, missing
  Python refusing a commit, idempotent installation, and preserving existing
  hook configurations. Nested test repos clear inherited Git paths so these
  checks also work while Git itself runs the fast suite from the hook.
- The living runner regression now checks a Python command from PATH, as used
  by Actions, in addition to explicit executable paths and failure aggregation.
- `bash -n tools/hooks/pre-commit tools/install-hooks.sh tools/run-tests.sh
  install-dashboard.sh`: passed.
- Workflow YAML parsed using PyYAML BaseLoader; both jobs and all four event
  triggers are present. Each workflow `run` block passed `bash -n`.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m
  py_compile tests/test_commit_gate.py tests/test_test_runner.py
  .loom/threads/72-test-gate.stitching/verify_clean_checkout.py`: passed.
- `git diff --check`: passed.

## Clean-checkout fixture check

`PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python
.loom/threads/72-test-gate.stitching/verify_clean_checkout.py` archives tracked
HEAD files and overlays only this stitch's runner/hook/tests/workflow. It runs
`tools/run-tests.sh all` without the local patch library, local installation,
or uncommitted show edits. See `clean-checkout.log` for the full results.
The first sandboxed attempt could not bind loopback ports; the retained run
used approval to launch Chromium and bind the temporary test servers.

The tracked-only run passed all 368 fast tests and attempted all 24 browser
journeys: 19 passed, five failed, returning status 1. The failures exactly
match the existing repair stitch: `verify_control_column_scroll.py`,
`verify_control_surface_component.py`, `verify_control_tab.py`,
`verify_manifest_param_visibility.py`, and `verify_preset_control_surface.py`.
There were no missing patch files or dependency imports. No journeys are
excluded from CI, and no local patch library needs to be copied there.

## Boundaries

This is local macOS software verification, not a hosted Ubuntu Actions run.
The remote schedule activates after this commit is pushed to the default
branch with Actions enabled; a local commit cannot activate GitHub's scheduler.
Scheduled runs can be delayed, and GitHub can disable public-repository
schedules after 60 days of inactivity. No Pi, real-LAN, Pd, audio, or iPad
checks were run. Browser repairs remain owned by `5-browser-tier-red`.
