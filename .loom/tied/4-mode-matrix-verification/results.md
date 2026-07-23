# Physical-device control mode matrix — results

The execution and physical planes are covered by durable living regressions.

- `tests/test_device_control_routing.py` checks every OSC-backed Devices-tab
  helper against distinct execution and physical destinations in Live,
  Simulation, and Patch Edit. It also checks master and MUTE ALL execution
  routing, edit-mode availability, restore-live isolation, and host-only
  Forget behavior.
- `tests/test_device_enabled.py` checks explicit enable/disable, positive
  v1.10 wire and report vocabulary, acknowledgement, persistence, node boot
  migration, failed-delivery behavior, and contract/reference consistency.
- `tests/verify_device_control_modes.py` runs the real Dashboard and Chromium
  with separate local audition and fake-physical UDP receivers. It checks
  appearance convergence, mismatch repair, mode transitions, Device
  enable/disable in Simulation and Patch Edit, MUTE ALL isolation, Live
  restoration, host-only aliasing, UI terminology, and browser errors.

The integration verifier used a random high UDP port and the Mac's own LAN
address for its fake physical receiver. It did not use production UDP 6660 or
send to Finn Jet.

## Verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
# 28/28 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_device_control_modes.py
# 12/12 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/device_aliases.py dashboard/state.py dashboard/osc_bridge.py \
  dashboard/server.py python/bopos.py tools/simfleet.py tools/audition.py \
  tests/test_device_enabled.py tests/test_device_control_routing.py \
  tests/verify_device_control_modes.py \
  .loom/tied/2-dual-route-transport/verify_dual_route.py \
  .loom/tied/3-device-enable-ui-state/verify_device_enabled.py

node --check dashboard/static/js/dashboard.js
node --check dashboard/static/js/facilitator.js
git diff --check
```

All checks passed. The remaining `device_muted` occurrences are intentional
one-time migration reads/tests; the contract also retains the v1.5 spelling
only in its historical change log.

Finn Jet hardware has not been updated or exercised, and physical/audible
adoption remains unverified. No `.pd` file and no network port changed.
