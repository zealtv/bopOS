# Verification

Passed:

```sh
node --check dashboard/static/js/control-host.js
node --check dashboard/static/js/control-column.js
node --check dashboard/static/js/target-picker.js
~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
./tools/run-tests.sh fast
```

The browser-free suite passed 269 tests. `tests/verify_control_tab.py` was
updated for single-target cards, migration, duplicate prevention, derived
order, transient drafts, close, and reload persistence; it compiles.

The focused Playwright run could not launch Chromium in this managed macOS
sandbox: AppKit aborted because its required `SystemAppearance` bundle is not
visible. Browser behavior remains to be exercised in the final regression
child or a normal repository shell. No iPad, hardware, audio, or Pure Data
verification was performed.
