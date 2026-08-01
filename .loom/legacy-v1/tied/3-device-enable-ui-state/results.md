# Device enabled wire, state, and UI — results

The persistent physical control is now consistently positive Device
enabled/disabled.

- Wire request: `/all/os/to <uid> enabled <0|1>`.
- Receipt: `/os/enabled <uid> <device-enabled> <output-enabled>`.
- Report: `device_enabled`, `mute_all`, and `output_enabled`.
- Effective output: `device_enabled AND NOT mute_all`.
- Node and host persistence use `device_enabled`, default true.
- Legacy `device_muted` is inverted once and removed from canonical saves.
- simfleet and audition implement the v1.10 vocabulary and semantics.
- Dashboard public state, pending/current/unconfirmed convergence, Devices
  roster indicators, detail action, accessibility labels, report display, and
  facilitator output marker use the positive fields.
- The OSC contract and quick reference are v1.10. No compatibility alias for
  the retired exact-device `mute` verb remains.

## Verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/37-physical-device-control-routing/3-device-enable-ui-state.stitching/verify_device_enabled.py
# 12/12 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/2-dual-route-transport/verify_dual_route.py
# 7/7 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
# 16/16 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/device_aliases.py dashboard/state.py dashboard/osc_bridge.py \
  dashboard/server.py python/bopos.py tools/simfleet.py tools/audition.py \
  .loom/threads/37-physical-device-control-routing/3-device-enable-ui-state.stitching/verify_device_enabled.py

node --check dashboard/static/js/dashboard.js
node --check dashboard/static/js/facilitator.js
git diff --check
```

All checks passed. Browser/mode-matrix coverage is owned by child stitch 4.
Finn Jet hardware has not yet been updated or exercised. No `.pd` file or
network port changed.
