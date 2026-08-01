# Verification

Focused verifier:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/ui-tabs/tabs-3-next-sweep/07-seats-workspace.stitching/verify_seats_workspace.py
```

Result on 2026-07-15: **15 passed**.

The suite covers strict Seat key/ID and unique-UID loading, reindex migration
and persistence rollback, current-preset cleanup on delete, preserved offline
venue bindings, confirmation and one-to-one binding behavior, acknowledgement-
before-mutation ordering for unbind/replacement/removal, timeout atomicity for
removal and venue load, stale unbound heartbeat quarantine, and static UI
ownership assertions for the Seats and Devices noun boundary. It also proves
that moving an online UID revokes both changed assignments, and that offline
displacements stay quarantined until reconnect unassignment is acknowledged.

Real-dashboard browser verifier:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/ui-tabs/tabs-3-next-sweep/07-seats-workspace.stitching/verify_seats_workspace_browser.py
```

Result on 2026-07-15: **12 passed** against the real dashboard server and two
unassigned `simfleet` nodes. It creates a Seat, inspects the noun boundary,
renames and positions an element, sends Identify, assigns a physical simulator,
reindexes while preserving that binding, inspects the Devices detail boundary,
and deletes the Seat through the acknowledged live-unassignment path. Browser
evidence is retained as `01-seats-workspace.png` and `02-device-boundary.png`.

Adjacent verification:

- Python compile checks and JavaScript syntax checks passed for every touched
  Python/JavaScript module.
- The tied UID-admin verifier passed 23/24 checks. Its sole old expectation —
  that an out-of-band `/all/os/assign` can leave an unbound node at ID 7 — is
  intentionally superseded: this stitch now quarantines that stale identity and
  UID-unassigns it. The focused browser pass above proves ordinary assignment
  through the authoritative Seat transaction instead.
- Older `d8-1-seat-model`, `03-seat-identity-leaks`, `tabs-1-skeleton`, and
  `01-simulation-transition-coherence` browser paths refer to replaced controls
  (`#device-bind`, `#simulate-toggle`) or pre-quarantine unbound IDs. Their
  affected behavior is covered by the stitch-local suites above; their
  unrelated checks passed up to those superseded expectations.

These focused runs did not exercise real UDP packet loss, a physical node, iPad
touch interaction, or audible output. Those remain outside this software-only
stitch-local verification.
