# fp-3 verification results — 2026-07-14

## Outcome

The technical dashboard now presents one fleet-level desired patch selector,
confirmation-gated Set and Revert actions, and a deterministic convergence
summary. Assigned and unbound device rows carry compact observed-state badges.
Device detail is diagnostic-only for patches: it shows desired and observed
identity, inventory, fetch state, manifest/source facts, targeted Retry or
Re-switch, and Pull latest for an active Git-managed patch. Per-device patch
selection, switching, sending, and patch sync are absent. Asset Send and Sync
remain device-addressable.

The public WebSocket state resolves `fleet_patch.fingerprint` through the live
host catalog, matching the identity used to derive stale badges. The durable
staged identity is unchanged.

## Focused verification

Command (run outside the filesystem sandbox because it binds local TCP/UDP
ports and launches headless Chromium):

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-3-fleet-ui.stitching/verify_fp3_fleet_ui.py
```

Result: **13/13 passed** against the real `dashboard/server.py`, two real
`tools/simfleet.py` nodes, and headless Chromium on non-default dynamic ports.

Coverage:

- every ratified badge spelling, including `stale (unverified)`;
- one confirmation-gated selector converging two assigned nodes;
- deterministic summary and compact row badges;
- diagnostic inventory and desired/reported content identities;
- absence of ordinary per-device patch selector, Switch, and Send Patch;
- asset Send and Sync still available and an asset fetch reaching `in sync`;
- host edit producing two `stale` rows and distinct desired/reported digests;
- targeted stale Retry, wrong-name `mismatch`, and Re-switch;
- second fleet choice enabling Revert, then Revert restoring the prior patch.

## Regressions and static checks

Passed:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/distribution-workflow/verify_distribution_ui.py
# 5/5 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/d8-2-simulate-toggle/verify_d8_simulation.py
# 9/9 passed

node --check dashboard/static/js/dashboard.js

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py \
  .loom/threads/fleet-patch/fp-3-fleet-ui.stitching/verify_fp3_fleet_ui.py

git diff --check
```

The tied fp-2 verifier passed its first **23 checks**, through beginning a fresh
Revert fetch, then stalled in its older overlapping same-content Revert fixture
and was interrupted. Its final static assertion also requires the legacy UI to
contain `ws.send("switch_patch", ...)`; fp-3 deliberately removes that
per-device/simulation UI path in favor of `set_fleet_patch`. The focused fp-3
browser suite exercises the replacement Set, Retry, Re-switch, stale, and Revert
paths end to end. No tied verification artifact was rewritten to conceal this
intentional UI contract change.

## Boundaries

No `.pd` file was edited. No real Pi, installation LAN, audible engine, iPad, or
touch interaction was tested; those remain the waiting fp-4 hardware gate and
later real-UI review. The current layout is pre-tabs, as required while
`ui-tabs/tabs-1-skeleton` remains waiting.
