# UID administration seam results

## Outcome

- OSC contract v1.5 defines the exact allowlisted
  `/all/os/to <uid> <verb> [args...]` administration envelope and requires
  uid-bearing `/os/rev` receipts.
- Real nodes, simfleet and audition tooling isolate the seven ratified verbs by
  opaque uid. No recursive OSC dispatch is used; parameters, probes, patch and
  asset distribution, storage and mute cannot enter the envelope.
- `unassign` persists an explicit `id=-1` tombstone before changing runtime or
  engine identity, so a `bopos.devices` seed cannot resurrect a revoked ID. It
  keeps hostname, clears positions and wakes an immediate heartbeat.
- Dashboard individual actions and report requests use uid routing whether the
  device is bound or unbound. Fleet actions retain `/all`; the legacy
  `/all/os/identify <uid>` node spelling remains compatible.
- Unbound detail exposes Identify, Report and the four safe individual admin
  actions. Content diagnostics remain read-only; Retry and Git Pull are hidden.
- `OSCBridge.unassign()` supplies the awaited heartbeat handshake and suppresses
  authoritative assignment replay while revocation is in flight, ready for
  stitch 07's binding transactions.

## Verification

Passed:

```sh
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile python/bopos.py dashboard/osc_bridge.py dashboard/server.py tools/simfleet.py tools/audition.py .loom/threads/ui-tabs/tabs-3-next-sweep/08-unbound-admin-seam.stitching/verify_uid_admin.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/threads/ui-tabs/tabs-3-next-sweep/08-unbound-admin-seam.stitching/verify_uid_admin.py
```

Result: **24/24 passed**. Coverage includes wrong uid/verb/arity rejection,
uid-attributed lifecycle receipt, successful/idempotent/failed-persistence
unassign, real CSV-seed suppression, engine ID and heartbeat behavior, audition
isolation, dashboard replay suppression through acknowledgement, bound and
unbound action isolation, uid-targeted report v1.5, excluded content verbs,
browser errors, and clean process shutdown.

Adjacent current regressions:

```sh
PYTHONPATH=python:python/io PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/assign-persistence/test_assign_persistence.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/03-seat-identity-leaks/verify_seat_identity.py
```

Results: **29/29 passed** and **10/10 passed**.

Informational older-suite runs:

- `os-admin-verbs/test_admin_verbs.py`: **22/26 passed**. All 19 helper checks
  passed; four E2E assertions send the contract-removed `update` WebSocket verb
  instead of v1.3+ `updatebopos` and therefore receive no revisions.
- `dist-2-node-side/verify_dist2_node_side.py`: **37/40 passed**. Two assertions
  pin report version `1.3` and correctly observe new `1.5`; one active-fetch
  timing assertion failed while its subsequent coalescing/restart/terminal
  checks passed.
- `dist-3-dashboard-send/verify_dist3_dashboard_send.py` passed its first eight
  HTTP/static assertions, then timed out looking for the removed pre-seats
  `#assigned` sidebar fixture.
- `d8-3-binding-ux/verify_d8_binding_ux.py` uses the pre-tabs room surface and
  stopped before assertions when that hidden panel had no bounding box.

These historical artifacts were not edited. Their relevant current behavior is
covered by the focused verifier and the passing Seat regression above.

```sh
git diff --check
```

Result: passed.

## Review

A protocol-focused read-only survey and final diff audit found and closed:

- CSV assignment resurrection unless unassign persists a tombstone;
- assignment replay racing the `id=-1` acknowledgement;
- an unbound Git Pull content-control leak;
- incomplete canonical/compatibility contract spellings;
- missing bound-device UID-routing and real-seed test coverage.

The reviewer made no repository edits.

## Boundaries

This stitch provides the safe revocation primitive but deliberately does not
change existing bind/unbind/remove/forget/venue transactions; stitch 07 must
integrate `OSCBridge.unassign()` before claiming those paths safe. The ratified
seven-verb boundary excludes UID-targeted content distribution despite the older
08 instruction's broader wording. No physical node, installation LAN, audible
engine, iPad/touch browser or `.pd` file was tested or changed.

