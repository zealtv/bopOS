# Verification results

Date: 2026-07-16

## Focused protocol/node seam

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/seat-groups/seat-groups-3-delivery/seat-groups-1-core-implementation.tending/1-protocol-node.stitching/verify_group_protocol_node.py
```

Result: **37 passed, 0 failed**. This exercises canonical and invalid selectors;
numeric/all compatibility; assigned, unassigned, overlapping, and empty group
matching; exact replacement and clearing; invalid, duplicate, and UID-mismatched
envelopes; attributable sorted receipts and reports; persistence failure;
restart durability; same-Seat assignment, direct reassign, and unassign; flat and
nested provided terms; literal-all assignment/UID-envelope isolation; and
real-helper, simfleet, and audition parity.

## Adjacent regressions

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/1-contract-model-relay/verify_param_contract_relay.py
```

Result: **28 passed, 0 failed**.

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/08-unbound-admin-seam/verify_uid_admin.py
```

Result: the helper/audition/dashboard-handshake portion passed **15 checks**.
The older browser continuation did not complete: it timed out waiting for the
second simulator's unassigned device row. This happened while the parallel
dashboard Seat-group state seam was changing dashboard production state and is
left for root's combined post-merge verification; no protocol/node assertion
failed before that UI wait.

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/seam-3-points-node-side/verify_points_node_side.py
```

Result: the real-helper assignment and point-decomposition portion passed **6
checks**. Its real dashboard/simulator continuation then stopped because its
discovery snapshot contained no simulated Seat 1. As with the UID browser
continuation, root should rerun the combined stack after both parallel children
are stable; no point-helper assertion failed.

## Static checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/groups.py python/bopos.py tools/simfleet.py tools/audition.py
git diff --check
```

Result: passed.

## Boundaries not verified

- No physical node, LAN broadcast, restart-on-Pi, or hardware/audio check was
  run.
- Audition protocol behavior was verified with virtual nodes and captured OSC;
  no engines were launched and no audible check was run.
- No browser or touch surface is owned by this child.
- No Pure Data change is required or made; group identity is removed before the
  unchanged engine-facing address.
