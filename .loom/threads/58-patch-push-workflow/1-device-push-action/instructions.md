# 1-device-push-action

**Status:** after `66-projects/1-remove-device-pins` · re-scoped 2026-10-04
**Goal:** the Device page always offers "push the patch to this device" when
the device can take it — not only when its badge shows a fault.

## Today

`patchDiagnostics` (`dashboard.js`) renders `#fleet-patch-retry` ("Sync to
pinned/fleet patch", sends `retry_fleet_patch`) only for fault badges
(`missing`, `stale`, `mismatch`, `failed`, …). Most of the time the badge reads
`current` and there's no button. The label names the mechanism, not the intent
(Bob says "update patch").

## Re-scoped from the ratified projects design (2026-10-04)

One patch per fleet, no pins. This becomes a plain **push the Patch to this
device** action on the Device page, always offered when the device can take
it — for a box that missed a push or was just swapped in. Label it in Bob's
words ("update patch"), not the mechanism. Replace `retry_fleet_patch`'s
fault-only button.

## Keep regardless

- Disabled-with-reason rather than hidden when the device can't take a push
  (offline, unassigned, simulated).
- Pushing restarts the engine → confirm.
- Test in a whole-fleet journey (`verify_device_patch_targeting.py` is deleted by `66/1`); hardware push on the rig is
  a separate claim.
