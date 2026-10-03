# 1-device-push-action

**Status:** waits on `66-projects/0-project-design` · re-scope before claiming
**Goal:** the Device page always offers "push the patch to this device" when
the device can take it — not only when its badge shows a fault.

## Today

`patchDiagnostics` (`dashboard.js`) renders `#fleet-patch-retry` ("Sync to
pinned/fleet patch", sends `retry_fleet_patch`) only for fault badges
(`missing`, `stale`, `mismatch`, `failed`, …). Most of the time the badge reads
`current` and there's no button. The label names the mechanism, not the intent
(Bob says "update patch").

## After `66/0`

With one patch per fleet and no pins, this likely becomes a plain "re-push the
project patch to this device" action — or disappears into the project's own
push. Rewrite this stitch from the ratified design, or drop it.

## Keep regardless

- Disabled-with-reason rather than hidden when the device can't take a push
  (offline, unassigned, simulated).
- Pushing restarts the engine → confirm.
- Test in `tests/verify_device_patch_targeting.py`; hardware push on the rig is
  a separate claim.
