# Verification

## Focused browser verification

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python tests/verify_manifest_param_visibility.py
```

Result: **7 passed, 0 failed**.

The check launches the real dashboard and simfleet, then verifies:

- the embedded desktop Control tab renders all mixed-flag manifest params;
- nested parameter structure remains visible;
- an unflagged numeric param retains generator authoring;
- standalone `/facilitator` renders only `dashboard: true`;
- Device control renders the full manifest;
- the Patch-tab checkbox reads `Facilitator`;
- no browser page errors occurred.

## Adjacent regressions

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python tests/verify_control_tab.py
```

Result: **15 passed, 0 failed**.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python tests/verify_control_surface_component.py
```

Result: **10 passed, 0 failed**.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m unittest tests.test_device_control_routing
```

Result: **5 passed, 0 failed**.

## Static checks

```sh
node --check dashboard/static/js/facilitator.js
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/server.py tests/verify_manifest_param_visibility.py
git diff --check
```

Result: all passed.

## Boundary

No hardware, iPad/touch, audio, or Pure Data verification was required or
performed. The focused check exercises Chromium desktop rendering and the
real dashboard/simfleet route.
