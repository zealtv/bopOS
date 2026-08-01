# Results — 06b-control-panel-atomic-mobile

## Verification

Passed:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_control_surface_component.py
  46 checks, including the 480px facilitator geometry

./tools/run-tests.sh fast
  255 tests

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_preset_control_surface.py
  isolated pass after the full-suite timeout

git diff --check
```

`./tools/run-tests.sh browser` passed 18/19 living journeys. The only red was
`verify_preset_control_surface.py`, which timed out waiting for its second
preset catalog update after its first save had already passed. It is unrelated
to the one-line facilitator CSS deletion and passed immediately in isolation,
including all 25 checks. Both changed-surface journeys
(`verify_control_surface_component.py` and `verify_control_tab.py`) passed in
the full run.

## Boundary

The measurement is Chromium layout evidence at 480 CSS pixels. No physical
phone or iPad touch check was performed. No Pure Data files were edited.

The unrelated pre-existing changes in `dashboard/shows/test.json` and
`.obsidian/` were left untouched.
