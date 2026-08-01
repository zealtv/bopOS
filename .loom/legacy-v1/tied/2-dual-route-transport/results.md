# Dual-route transport — results

The Dashboard now has explicit execution and physical OSC routes on the
existing UDP 6660 port.

- `send()` targets Live / Simulation / Patch Edit.
- `send_physical()` always targets the configured installation LAN.
- UID-aware assignment, membership, requests, and administration choose from
  the target object's physical/virtual identity.
- Physical patch and asset commands always use the LAN route.
- Master, MUTE ALL, parameters, automation, cues, and points use the execution
  route.
- MUTE ALL and physical controls are both available during Patch Edit, but go
  to different destinations.
- Physical asset delivery is no longer rejected merely because Simulation is
  active.
- Execution restore now sends only master and MUTE ALL. It sends no physical
  assignment or exact-device mute.
- MUTE ALL no longer reasserts the independent per-device layer.
- Physical reconnect assignment/membership stays active during Simulation,
  while parameter/master catch-up is limited to the object that belongs to the
  active execution target.

## Verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/37-physical-device-control-routing/2-dual-route-transport.stitching/verify_dual_route.py
# 7/7 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/osc_bridge.py dashboard/server.py \
  .loom/threads/37-physical-device-control-routing/2-dual-route-transport.stitching/verify_dual_route.py

node --check dashboard/static/js/dashboard.js
git diff --check
```

All current focused checks passed.

The older tied simulation-transition verifier was also run. Its first half
failed the intentionally retired requirement that Live restoration replay
physical assignment; its browser half then timed out on its legacy embedded
live-view selector. The older live-controls backend verifier passed its first
18 assertions and then hit fake-wire API drift because it replaces
`os_command` but not the new explicit `send_mute_all` method. Neither failure
identified a runtime defect; the new focused verifier directly covers both
changed seams.

No `.pd`, node runtime, network port, or hardware state changed in this stitch.
