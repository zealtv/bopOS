# Verification

Passed:

```sh
node --check dashboard/static/js/control-column.js
node --check dashboard/static/js/facilitator.js
~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
./tools/run-tests.sh fast
```

The browser-free suite passed 269 tests. The focused Control/Remote journey now
asserts exhaustive derived order, absence of picker and presets, and preserved
Remote device commands. Its browser launch remains blocked in this managed
macOS sandbox by the hidden `SystemAppearance` bundle; the final regression
child will retain that honest boundary. No iPad, hardware, audio, or Pure Data
verification was performed.
