# Dashboard Seat-group core verification

Implemented the dashboard-owned core seam in `dashboard/state.py`,
`dashboard/osc_bridge.py`, and `dashboard/server.py`. No production HTML, CSS,
client JavaScript, node, simulator, audition, OSC-contract, live-control, or
Pure Data files were changed by this child.

## Focused verification

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/seat-groups/seat-groups-3-delivery/\
seat-groups-1-core-implementation.tending/2-dashboard-state-sync.stitching/\
verify_group_dashboard_state.py
```

Result: **6/6 tests passed**.

Coverage includes catalog and membership validation, durable monotonic IDs
that are not reused after deletion, restart, or venue rollback,
multiple and empty groups, deletion cleanup and failed-save rollback, venue
round-trip, preset exclusion, state API create/rename/delete/membership
operations, offline and unbound retention, exact and stale receipts, bounded
retry exhaustion that repeated stale receipts cannot extend, reconnect replay,
report mismatch repair, bind/unbind/direct replacement behavior, assignment
gating that waits for a later matching-ID heartbeat before membership, and
membership edits during that wait staying transport-gated while the later
heartbeat sends exactly the latest full state, plus
durable nested group-parameter fan-out before one
`/g<id>/p/...` datagram.

## Adjacent regressions

- `.loom/tied/07-seats-workspace/verify_seats_workspace.py`: **15/15 passed**.
- `.loom/tied/2-dashboard-state-editor/verify_param_dashboard_backend.py`:
  **13/13 passed**.
- `.loom/tied/2-dashboard-state-editor/verify_param_dashboard_browser.py`:
  **12/12 passed**, with no page errors.
- `py_compile` passed for all three dashboard production files and the focused
  verifier; `git diff --check` passed.

The broader `08-unbound-admin-seam` verifier passed its helper, node,
audition, handshake, dashboard-start, and bound-action checks, then timed out
in its browser phase waiting for a simulated unassigned device while the
parallel protocol child was actively changing `tools/simfleet.py`. Root should
rerun that integration check after both children are stable.

## Boundaries and limitations

- Transport behavior is verified with encoded OSC datagrams through a fake
  sender, as required by the child contract. Root owns real protocol-child
  integration.
- No physical LAN, Raspberry Pi, browser touch, or audio-engine verification
  was performed.
- Group authoring and visualization production UI remain intentionally absent;
  only backend state operations are exposed for the delivery stitch.
- The group-parameter helper is backend-only; the promoted All/Group/Seat
  control surface remains reserved for dashboard live-controls.
