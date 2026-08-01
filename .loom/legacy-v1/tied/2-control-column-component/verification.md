# Verification — 2-control-column-component

## Static and focused

```text
node --check dashboard/static/js/control-column.js
node --check dashboard/static/js/facilitator.js
node --check dashboard/static/js/control-surface.js
~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
git diff --check
```

Result: all three JavaScript files parse; component ownership ran 5 tests,
all passing; the diff has no whitespace errors.

The existing `tests/verify_control_tab.py` journey was also run directly:
32 checks passed, including the embedded Control surface and standalone Remote
surface, with no page errors.

## Required tiers

```text
./tools/run-tests.sh fast
```

Result: 255 tests passed.

```text
./tools/run-tests.sh browser
```

Result: all 20 living browser journeys passed. In particular, the four
unchanged iframe-locating journeys passed:

- `verify_control_tab.py`
- `verify_event_control_panel.py`
- `verify_manifest_param_visibility.py`
- `verify_preset_control_surface.py`

The first browser invocation was sandbox-restricted and could not reserve
loopback ports or launch Chromium. The same command was rerun with local
port/Chromium permission and passed completely. This was an execution
environment boundary, not a test failure.

## Boundaries

No iframe retirement, second production column, layout persistence, visual
design, touch/iPad, real device, or Pure Data work was part of this refactor.
The unchanged browser surfaces are the relevant acceptance evidence.
