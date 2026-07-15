# Verification

## Outcome

- Devices presents one physical UID roster with all/online/offline/bound/unbound
  filters and explicit binding badges. The former duplicate unbound roster is
  gone.
- Bound and unbound detail share identity, health/version, content diagnostics,
  report, Identify and guarded UID-routed lifecycle actions.
- An unbound online device can be assigned to an empty Seat. The shortcut sends
  the existing `bind_seat` message and therefore uses the same locked,
  authoritative transaction as the Seats workspace. Bound detail links back to
  that Seat instead of authoring Seat state locally.
- Fleet-patch fingerprint drift remains visible per device and the existing
  convergence coordinator is exposed as one-click `Repair / Retry`.
- Devices now includes an explicit, confirmed Shutdown All action. Seat names,
  IDs, geometry and mix parameters remain absent.

## Focused real-dashboard gate

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/09-devices-workspace/verify_devices_workspace.py
```

Result on 2026-07-15: **18/18 passed** against the real dashboard server and two
unassigned simfleet nodes. The pass covers one-row-per-UID rendering, all five
filters, bound/unbound labels, detail facts, noun-boundary exclusions, direct
Identify and report, device-first assignment, return to Seats, confirmation and
UID routing for individual administration, confirmed Shutdown All, and no page
errors. It also stages a real host patch, mutates its fingerprint, observes the
stale device state, and reconverges it with the row repair action.

Browser evidence is retained as `devices-workspace.png`.

## Adjacent regressions

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/07-seats-workspace/verify_seats_workspace.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/07-seats-workspace/verify_seats_workspace_browser.py
```

Results: **15/15 passed** and **12/12 passed**. These retain the strict binding,
revocation, reindex and Seat-workspace behavior on both the focused model/server
surface and the real dashboard with simfleet.

The historical `fp-3-fleet-ui` browser artifact passed its first two static
checks, then timed out because it predates tabs and tries to interact with the
hidden Devices panel without opening it. It was not edited. Its relevant
current drift and single-device repair path is exercised end to end by the new
focused gate above.

## Static checks

```sh
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py dashboard/state.py \
  .loom/tied/09-devices-workspace/verify_devices_workspace.py
git diff --check
```

All passed.

## Boundaries

No physical node, installation LAN, packet loss, iPad/touch browser, audible
engine or Pure Data patch was exercised or changed. Shutdown All was proven
against the simulated fleet only.
