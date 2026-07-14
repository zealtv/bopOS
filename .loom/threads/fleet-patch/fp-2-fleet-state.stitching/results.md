# fp-2 verification results — 2026-07-14

## Outcome

Fleet desired state is now wired end to end. Confirmed `set_fleet_patch`
stages the live host fingerprint, converges eligible online nodes, and switches
only after content identity is proved. `revert_fleet_patch` uses the same path;
`retry_fleet_patch` remediates one missing/stale/mismatched node. Simulation
uses the same fleet record. Derived badges ride full state and device WebSocket
payloads without being stored on runtime devices.

`tools/simfleet.py --patches-dir` is the only simulator addition. It lets a
temporary host catalog and fake nodes use the same fingerprint root, so drift
and retry can be verified without editing repository patches.

## Focused verification

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-2-fleet-state.stitching/verify_fp2_fleet_state.py
```

Result: **26/26 checks passed** against the real dashboard backend and a real
`tools/simfleet.py` subprocess on non-default local ports.

Coverage:

- legacy seat `patch` removal, persistence, venue snapshot, simulation
  read-through, and previous rotation;
- all badge precedence cases and proof that verdicts are not persisted;
- unconditional set confirmation;
- stage → fetch → fingerprint proof → switch across two assigned nodes;
- an offline node remaining `unknown` without blocking healthy nodes;
- badge serialization on WebSocket state/device payloads;
- host edit → `stale` on catalog refresh → operator retry → `current`;
- row retry cannot cancel a fleet operation already converging other nodes;
- superseded retry receipts cannot switch a node back to an old choice;
- a same-content superseding operation safely observes the existing fetch
  generation without relabelling it;
- second fleet choice and Revert through the same convergence path;
- the legacy simulated-switch WS path rejects missing confirmation.

## Regressions

All passed:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/fp-1-identity-module/verify_fp1_identity.py
# all checks passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/distribution-workflow/verify_distribution_workflow.py
# 9/9 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/d8-2-simulate-toggle/verify_d8_simulation.py
# 9/9 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py dashboard/state.py dashboard/osc_bridge.py tools/simfleet.py \
  .loom/threads/fleet-patch/fp-2-fleet-state.stitching/verify_fp2_fleet_state.py

node --check dashboard/static/js/dashboard.js

git diff --check
```

## Boundaries

No `.pd` file was edited. This stitch is backend/protocol-state work: browser
UI coverage belongs to fp-3, and real-node/audio verification remains the
waiting fp-4 bop000 gate.
