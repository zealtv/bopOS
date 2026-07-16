# Results — Dashboard live controls

## Outcome

- Replaced device-owned promoted controls with Seat-owned All, Group, and Seat
  cards driven only by the valid staged host manifest. Flat and nested
  identities remain qualified end to end.
- All and Group aggregates show a concrete value only when every member Seat
  agrees. Empty Groups remain visible but disabled. Offline and unbound Seats
  retain controls and durable values.
- Added idempotent **Send all** actions for All Seats and each Seat. All replay
  expands in stable Seat-ID then manifest-declaration order and uses numeric
  Seat selectors so differing snapshots are preserved.
- Added the ratified exact-UID physical-device mute layer, persistent on the
  node and in the host-global device registry. The existing fleet safety mute
  remains a session overlay; effective mute is their logical OR.
- Added selected-Device Mute/Unmute and accessible Devices-roster indications
  for device mute, fleet mute, pending, and unconfirmed states. Fleet safety
  disables the individual action.
- Updated the real helper, simulator, audition rig, dashboard bridge/state,
  and OSC contract together. No `.pd` file changed.

## Focused verification

Run from the repository root on 2026-07-16:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/ui-tabs/tabs-3-next-sweep/12-dashboard-live-controls.stitching/verify_live_controls_backend.py
# 20/20 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/ui-tabs/tabs-3-next-sweep/12-dashboard-live-controls.stitching/verify_device_mute_protocol.py
# 13/13 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/ui-tabs/tabs-3-next-sweep/12-dashboard-live-controls.stitching/verify_live_controls_browser.py
# 16/16 passed
```

The browser suite ran outside the sandbox because it binds dynamic loopback
TCP/UDP ports and launches Chromium. It exercised the real dashboard and two
real simulator nodes at a 768 px touch viewport. Coverage includes the complete
flat/nested × All/Group/Seat surface, mixed aggregates, disabled empty Groups,
All/Seat replay activation, 44 px targets, no horizontal overflow, absence of
new help prose, exact mute convergence, roster/detail presentation, and fleet
overlay release. `live-controls-ipad.png` records the reviewed live surface.

The backend and protocol suites cover fail-closed schema loading, type/range
validation, durable offline/unbound Group updates before one datagram,
transaction rollback, stable numeric replay without state/master/mute mutation,
multiple unassigned nodes sharing ID `-1`, persistence across restart,
enforcement-before-receipt, old-node unconfirmed state, fleet-overlay OR
semantics, and Forget deleting mute intent with the alias registry entry.

## Regressions and static checks

- Device alias registry: **16/16 passed**.
- Seat-group node/protocol/audition regression: **37 checks passed**.
- Device asset inventory: **27/27 passed**.
- Adjacent nested-parameter backend and contract/model/relay regressions:
  **41/41 passed**.
- Python compilation, both JavaScript syntax checks, and `git diff --check`
  passed.
- The older alias integration browser suite passed its first eight current
  identity checks, then waited for the intentionally removed device-owned
  facilitator `.card`; the focused live-controls browser suite verifies its
  Seat-owned replacement. The older facilitator-promotion browser is likewise
  superseded by this deliberate surface change.

## Remaining boundaries

No real Pi, hardware mixer, engine-stop fallback, installation LAN, audible
output, Safari/iPad hardware, or screen reader was exercised. Chromium touch
emulation verifies layout and pointer activation but is not a claim about real
iPad Safari. Persistent device mute remains honestly unconfirmed on older nodes
that do not implement the additive receipt/report fields.
