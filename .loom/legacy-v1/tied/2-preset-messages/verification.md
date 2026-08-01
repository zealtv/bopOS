# Verification — 2-preset-messages

Date: 2026-07-29.

## Passed

- Python compile:
  `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/show_model.py dashboard/show_engine.py dashboard/server.py tests/test_show_model.py tests/test_preset_application.py`
- JavaScript parse:
  `node --check dashboard/static/js/show.js`
  and `node --check dashboard/static/js/facilitator.js`
- Focused model/application:
  `~/.venvs/bopos/bin/python tests/test_show_model.py` — 21 passed.
  `~/.venvs/bopos/bin/python tests/test_preset_application.py` — 22 passed.
- Browser-free suite:
  `./tools/run-tests.sh fast` — 245 passed.
- Focused real-dashboard browser journey:
  `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python
  .loom/threads/41-preset-primitive/09-show-integration/2-preset-messages.stitching/verify_preset_messages.py`
  — 6 passed, 0 failed. It authored a fingerprinted timed PRE reference,
  played it, observed only expanded `/p/*` sends in Monitor, confirmed the
  pre-commit omission count, captured a named-group step through the Control
  iframe, and observed no page errors.
- Relevant existing browser journeys passed inside the full sweep:
  Control tab, Show reference foundation, preset Control/Device surface,
  preset editor, event panel, live param kinds, Monitor globals, manifest
  visibility, precision input, Device control/targeting, patch hand-off, log
  destination, and OSC transport Monitor.

## Full browser boundary

`./tools/run-tests.sh browser` completed 15/17 living journeys green. Two
unrelated pre-existing checks remained red:

- `verify_control_surface_component.py`: its synthetic enum probe writes one
  `<select>` and dispatches on a second freshly queried element, so the last
  send remains an earlier parameter.
- `verify_generator_drawer.py`: simfleet density ticks continue after its Stop
  assertion even though dashboard automation clears.

Both reproduce unchanged from an archive of pre-stitch `HEAD` at
`/tmp/bopos-preset-baseline.o30FEO`; neither changed surface is touched by this
stitch. The failures are recorded rather than folded into unrelated work.

## Not verified

No physical device, installation LAN, iPad/touch, Pure Data, or audible check
was run. This stitch adds no PD edit or new wire form.
