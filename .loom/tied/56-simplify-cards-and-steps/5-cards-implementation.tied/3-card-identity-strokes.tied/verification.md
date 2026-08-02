# Verification

Passed:

```sh
node --check dashboard/static/js/group-slots.js
node --check dashboard/static/js/dashboard.js
node --check dashboard/static/js/control-column.js
node --check dashboard/static/js/control-host.js
node --check dashboard/static/js/facilitator.js
~/.venvs/bopos/bin/python tests/test_card_identity.py
~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
./tools/run-tests.sh fast
```

The new focused identity test passed 4 checks; component ownership passed 5;
the full browser-free suite passed 273 tests. Visual/browser verification is
still blocked in the managed macOS sandbox by Chromium's unavailable
`SystemAppearance` bundle and is carried honestly to the regression child. No
iPad, hardware, audio, or Pure Data verification was performed.
