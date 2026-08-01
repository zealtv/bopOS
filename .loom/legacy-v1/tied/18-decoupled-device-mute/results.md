# Decoupled device mute — results

Persistent exact-device mute can now be changed while the session fleet safety
overlay is active. Effective node mute remains the logical OR of the two layers,
so preparing a device's post-release state cannot make it sound while fleet
safety is on.

The selected Device Mute/Unmute action remains enabled under fleet mute. Each
Physical devices roster icon now reflects only persistent device intent and its
pending/current acknowledgement status; the global fleet overlay no longer
slashes or recolours every device row.

## Verification

Passed on 2026-07-16:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/18-decoupled-device-mute/verify_decoupled_device_mute.py
# 7/7

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/12-dashboard-live-controls/verify_device_mute_protocol.py
# 13/13

node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py \
  .loom/tied/18-decoupled-device-mute/verify_decoupled_device_mute.py
git diff --check
```

The focused real Dashboard + simfleet browser sequence proves both directions:
fleet on → device on → fleet off stays muted, and fleet on → device off remains
effectively safe until fleet release. Visual evidence is
`decoupled-device-mute.png`.

No wire, node, simulator, audition, or `.pd` change was required because their
two-layer OR model already supported this behavior. Real Pi hardware and audible
output were not exercised.
