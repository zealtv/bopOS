# Seat-group core verification

Date: 2026-07-16

## Focused child seams

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/1-protocol-node/verify_group_protocol_node.py
```

Result: **37 passed, 0 failed** across the real helper, simfleet, audition,
canonical selectors, membership persistence, receipts/reports, safe assignment
transitions, and flat/nested parameter relay.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/2-dashboard-state-sync/verify_group_dashboard_state.py
```

Result: **6/6 tests passed** across durable catalog/membership state, monotonic
IDs, venue state, preset exclusion, backend APIs, bounded convergence,
assignment ordering, reconnect/report repair, and parameter fan-out.

The dashboard child also passed the Seats workspace regression (**15/15**),
parameter backend regression (**13/13**), and parameter browser regression
(**12/12**, no page errors).

## Combined production seam

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/seat-groups/seat-groups-3-delivery/\
seat-groups-1-core-implementation.tending/verify_group_core_integration.py
```

Result: **passed**. The check uses production `InstallationState`, `OSCBridge`,
OSC encoding/decoding, and `SimFleet`. It proves one full-state membership
envelope reaches the intended simulated node, the attributable receipt moves
dashboard convergence to `current`, both bound and unbound member Seat mirrors
are updated, and one `/g3/p/gain0` packet reaches the group member.

## Adjacent retained verifiers

- Nested parameter contract/model/relay: **28/28 passed**.
- UID-admin: its first **15 checks passed**, then the browser phase used removed
  `#unassigned` markup. Browser state already held all three devices; the
  Devices redesign now uses `#device-roster` with the `unbound` filter. This is
  a stale tied-verifier selector, not a discovery or Seat-group failure.
- Point node-side: its helper section passed **6/6**, then its simfleet process
  had already exited because the tied verifier still passes the removed
  `--meter-interval 0` option. The stack continuation therefore saw no devices.
  This predates Seat groups and never reached group or point routing.

The two unrelated tied verifiers were not edited as part of this stitch. The
new combined production-seam verifier supplies the required current
dashboard/simfleet integration evidence.

## Static checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/groups.py python/bopos.py dashboard/state.py dashboard/osc_bridge.py \
  dashboard/server.py tools/simfleet.py tools/audition.py \
  .loom/threads/seat-groups/seat-groups-3-delivery/\
seat-groups-1-core-implementation.tending/verify_group_core_integration.py
git diff --check
```

Result: passed. No `.pd` file was changed.

## Boundaries not verified

- No physical node, installation LAN broadcast, Raspberry Pi restart, or
  hardware/audio check was run.
- No new production group UI is part of this core stitch; browser/touch review
  belongs to the delivery stitch.
- No Pure Data edit was required. The group selector is removed before the
  existing engine-facing parameter address is relayed.
