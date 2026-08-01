# Verification

## Outcome

- Patches exclusively owns the sole desired fleet-patch selector, Deploy and
  Revert. The production selector is visibly distinct from the contextual host
  patch selected for editing.
- Deploy/Revert continue to use the existing single `fleet_patch` record and
  generation-safe convergence coordinator. No second desired-state record was
  introduced.
- Devices retains observed-versus-desired patch diagnostics. A repairable bound
  exception exposes exactly one **Sync to fleet patch** action.
- Devices no longer contains production selection or deployment controls.

## Ratified unbound boundary

The stitch instruction asked for exception repair for bound and unbound
targets, but the later ratified v1.5 boundary is authoritative: the UID envelope
explicitly excludes content distribution and patch switching, and ordinary
content messages remain `all | Seat ID` selector-addressed. Multiple unbound
nodes all advertise ID `-1`, so a dashboard cannot uniquely target one without
an unratified wire or transport design.

Accordingly, an unbound device remains fully inspectable and shows desired and
observed patch facts, but its detail explains that it must be assigned before
content sync. No Sync button is rendered, and a forged `retry_fleet_patch`
request receives an explicit backend error instead of silently doing nothing or
broadcasting to every unbound node. This preserves the ratified safety boundary
rather than reopening the OSC contract inside an implementation stitch.

## Focused real-dashboard gate

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/10-patches-fleet-workflow/verify_patches_fleet_workflow.py
```

Result on 2026-07-15: **10/10 passed** against the real dashboard server, one
bound simfleet node and one unbound simfleet node. It proves exclusive Patches
ownership, separation from the editor choice, one desired record, confirmed
Deploy, assigned-node convergence, real host-fingerprint drift, one-device Sync
repair, the UI/backend unbound guard, confirmed Revert through the same
coordinator, and no browser errors.

Browser evidence is retained as `01-patches-fleet.png` and
`02-device-exceptions.png`.

## Adjacent regressions

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/02-patch-switch-terminal-state/verify_patch_switch_terminal.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/07-seats-workspace/verify_seats_workspace.py
```

Results: **12/12 passed** and **15/15 passed**. These retain bounded terminal
switch/retry behavior and the authoritative Seat transaction boundary.

The historical `fp-2-fleet-state` verifier passed **25/26** checks. Its sole
failure is an old static assertion requiring the removed legacy
`ws.send("switch_patch"...)` UI spelling; all fleet-state, convergence,
generation, drift, retry and Revert behavior checks passed. The artifact was not
edited.

## Static checks

```sh
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py \
  .loom/tied/10-patches-fleet-workflow/verify_patches_fleet_workflow.py
git diff --check
```

All passed.

## Boundaries

No physical node, installation LAN, packet loss, iPad/touch browser, audible
engine or Pure Data patch was exercised or changed.
