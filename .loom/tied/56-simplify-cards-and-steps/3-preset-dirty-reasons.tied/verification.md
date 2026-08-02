# Verification

Passed on 2026-08-02:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_preset_application.py
# 26 tests, OK

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile dashboard/preset_application.py dashboard/server.py \
  tests/test_preset_application.py

./tools/run-tests.sh fast
# 266 tests, OK

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_preset_control_surface.py

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_preset_editor.py
# both affected browser journeys passed
```

The focused coverage exercises clean, value-deviated, foreign-patch, and
deleted-preset-file states. This host-state change does not alter OSC, Pure
Data, hardware, or browser presentation; the distinct UI treatment is the
dependent `3-preset-dropdown-menu` stitch.
