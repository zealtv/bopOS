# Verification

Passed on 2026-08-02:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_preset_menu.py
# 3 tests, OK

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
# 5 tests, OK

node --check dashboard/static/js/control-surface.js
node --check dashboard/static/js/dashboard.js

./tools/run-tests.sh fast
# 269 tests, OK
```

The living Playwright journeys were updated for the merged menu across Control,
Device, and Patch editor, including a genuinely truncated long name, all three
actions, recall-none, disabled/unreadable entries, dirty/missing treatment,
delete confirmation, and the heartbeat-safe typed-name regression.

The focused browser command could not execute in this managed sandbox. Without
an override, Playwright's driver was denied `/System/Library/OpenSSL/openssl.cnf`;
with `OPENSSL_CONF=/dev/null`, Chromium launched but aborted because its bundled
`icudtl.dat` was unavailable to the sandbox. No browser pass is claimed here.
No hardware, touch/iPad, audio, OSC, or Pure Data behavior changed or was tested.
