# Verification

## Change

`tests/verify_control_surface_component.py` now creates `#surface-probe`
inside a dedicated `.live-card` immediately after `#cards`. The fixture still
resolves the shipping panel-scoped CSS, but facilitator heartbeat renders can
replace `#cards` without deleting it. No assertions or production code
changed.

## Results

- `~/.venvs/bopos/bin/python tests/verify_control_surface_component.py`
  — passed once after the edit.
- The same command was then launched in ten independent fresh processes:
  **10/10 passed**. Each process launched a fresh dashboard, two-device
  simfleet, and headless Chromium session.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m
  py_compile tests/verify_control_surface_component.py` — passed.
- `./tools/run-tests.sh fast` — **184 tests passed**.
- `./tools/run-tests.sh browser` — **12/12 living browser suites passed**:
  control surface, Control tab, Device modes, Device panel, Device patch
  targeting, generator drawer, live-param kinds, log destination, manifest
  visibility, OSC transport Monitor, precision input, and Set patch handoff.

The first sandboxed browser-suite attempt was denied loopback socket access
before any test bodies ran. The recorded browser result is the subsequent
canonical run with local-network permission.

## Boundaries

This is a browser-test fixture repair. It changes no dashboard runtime
behavior, OSC behavior, persistence, hardware, Pure Data, audio, touch, or
real-LAN behavior; none of those surfaces required separate adoption testing.
