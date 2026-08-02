# Verification

Passed:

```sh
node --check dashboard/static/js/control-cards-model.js
node --check dashboard/static/js/control-host.js
node --check dashboard/static/js/control-column.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  tests/test_control_cards_model.py tests/test_cards_grid_css.py \
  tests/verify_control_tab.py tests/verify_control_column_scroll.py
~/.venvs/bopos/bin/python tests/test_control_cards_model.py  # 4 passed
~/.venvs/bopos/bin/python tests/test_cards_grid_css.py       # 4 passed
./tools/run-tests.sh fast                                    # 281 passed
```

Attempted:

```sh
OPENSSL_CONF=/dev/null PLAYWRIGHT_BROWSERS_PATH=/tmp/bopos-playwright \
  ./tools/run-tests.sh browser
```

All 24 browser journeys failed before navigation at the same environment
boundary: macOS AppKit aborted Chromium because the managed sandbox hides the
required `SystemAppearance` bundle. This is not reported as an application
failure or a browser pass. `verify_control_tab.py` and
`verify_control_column_scroll.py` contain the new behavioral assertions and
compile, but must be run in a normal repository shell for rendered proof.

No iPad/touch, hardware, audio, network-installation, or Pure Data verification
was performed.
