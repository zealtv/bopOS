# Verification — 1-capture-retirement

## Focused static and browser-free checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py dashboard/state.py dashboard/show_model.py \
  tests/test_preset_application.py tests/test_show_model.py \
  tests/test_css_component_ownership.py \
  tests/verify_show_reference_foundation.py
node --check dashboard/static/js/control-host.js
node --check dashboard/static/js/show.js
~/.venvs/bopos/bin/python tests/test_show_model.py
~/.venvs/bopos/bin/python tests/test_preset_application.py
~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
```

Result: PASS. Python and JavaScript syntax checks passed; the three focused
browser-free modules ran 21 + 24 + 5 = 50 tests, all green.

## Focused browser journey

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache \
  ~/.venvs/bopos/bin/python tests/verify_show_reference_foundation.py
```

The first completed run failed in the pre-existing target-picker portion
because the capture deletion had left `capture?.handle(event)` in Show's click
handler. Its page-error list named `capture is not defined`; the dead hook was
removed. The corrected run passed 10 checks with 0 failures and no page errors,
including:

- the Show inspector hand-authors a stored preset as a reference message;
- the persisted message is `kind: "reference"` at `/preset/alpha/Dawn`;
- the strict preset schema reference survives persistence.

## Repository tiers

```sh
./tools/run-tests.sh fast
./tools/run-tests.sh browser
```

Result: PASS.

- fast: 263 tests, all green.
- browser: 24 journeys, all green. The retired
  `verify_show_capture.py` journey is no longer discovered; the surviving Show,
  Control, preset, target-picker, and component journeys all passed.

## Boundary

No hardware, Pure Data, real-LAN, audible, or iPad verification was run or is
required for this desktop authoring-feature deletion. No `.pd` file changed.
