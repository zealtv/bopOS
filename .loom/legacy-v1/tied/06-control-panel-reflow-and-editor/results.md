# Results — 06-control-panel-reflow-and-editor

## Shipped

- Atomic numeric parameter rows and a non-reflowing 320px generator drawer.
- A 340px ControlSurface card minimum, measured at a 360px viewport.
- Patch editor adoption of the shared parameter hierarchy, value boxes,
  generator drawer, event rows, and preset row.
- Single-member editor state with isolated `editor` automation.
- Declared events removed from the duplicate scratch UI; undeclared event
  testing remains.
- Neutral card treatment for the editor panel.
- Editor-aware automation validation, edit-mode gating, and resolved-target
  OSC recording.
- Ratified design-language supersession for the old wrapping rule.

## Verification

Passed:

```text
node --check dashboard/static/js/control-surface.js
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py dashboard/osc_bridge.py \
  tests/verify_preset_editor.py tests/verify_precision_param_input.py
~/.venvs/bopos/bin/python tests/test_preset_application.py
  24 tests
~/.venvs/bopos/bin/python tests/test_event_plane.py
  11 tests
~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
  5 tests
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_preset_editor.py
  22 checks
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_precision_param_input.py
  13 checks
./tools/run-tests.sh fast
  255 tests
./tools/run-tests.sh browser
  19/19 journeys
git diff --check
```

The focused editor journey uses the real dashboard in Patch Edit with
`--sim-no-engine --sim-audio-backend none`. It verifies shared markup,
single-member solid state, card background, phone reflow geometry, the fixed
drawer, editor-isolated automation, audition-engine generator ticks, declared
event fire, and the existing preset lifecycle.

## Boundaries

No Pure Data files were edited. Real PD/GUI behavior, audible output, real
iPad/touch interaction, and physical hardware were not tested; those remain
hardware adoption checks. The 360px Chromium measurement is layout evidence,
not an actual-phone touch check.

The unrelated pre-existing changes in `dashboard/shows/test.json` and
`.obsidian/` were left untouched and are not part of this stitch.
