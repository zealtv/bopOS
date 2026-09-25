# 58-patch-push-workflow

**Goal:** "push this patch to this device" is always available on the Device
page, pin/unpin is one visible toggle, and a bad patch can't knock a device off
the network.

**Status:** `5` and `6` tied. `1`, `3`, `4` ready; `2` blocked on `1`.

## Origin (Bob, 2026-08-05)

Pushing an edited `fire-button` patch to Ciro Toast failed
(`incident-2026-08-05-ciro-toast.md`):

> "there's currently no 'update patch' button on the device page. only 'pin to
> device' on the patch page … and a simpler pin/unpin button to get the device
> to hold onto a patch"

What was actually going on:

1. **Device was offline** — its stale on-device manifest used retired grammar,
   `start-engine.sh` rejected it, and `start.sh`'s error trap stopped the whole
   stack including `bopos.py`. Off the network means patch distribution can't
   fix it; recovery needed SSH. → `4`
2. **Push targets silently vanish when offline.** The Patch tab's target list
   only includes seat-bound, online, non-virtual devices; the Device tab's button
   also needs `online`. → `3`
3. **No push button at rest.** `Sync to pinned patch` (`retry_fleet_patch`,
   already correct) only renders when the badge shows a fault. → `1`

## "Pin to device won't push if already pinned"

Not what the code does: `set_device_patch` always re-pins and re-converges.
The symptom is explained by the device being absent from the dropdown. Bob
(2026-09-25) doesn't remember which he saw; **not critical**, because pinning is
due for a refactor soon. Don't open a separate bug for it.

Verified working: desired fingerprint is re-resolved from the host catalog on
every broadcast, so a host-side edit does show the device as `stale`. Detection
works; only the affordance is missing.

## Stitches

- ~~`5-fetch-tombstone-lockout`~~ — tied 2026-08-13. Stale fetch records blocked
  every later push to that device/slot.
- ~~`6-dashboard-url-advertisement`~~ — tied 2026-08-17. Dashboard told nodes to
  fetch from `0.0.0.0`.
1. `1-device-push-action` — always-available push on the Device page. Ends with
   a proposal to Bob.
2. `2-pin-unpin-toggle` — pin as a two-state control on the device. Needs `1`'s
   ruling. **Pinning is due for a refactor soon (Bob, 2026-09-25)** — confirm
   scope with Bob before claiming.
3. `3-push-target-legibility` — say *why* a device can't be pushed to, instead
   of hiding it.
4. `4-invalid-manifest-lockout` — node-side: bad patch must not take `bopos.py`
   down. Independent; claimable in parallel.

## Constraints

- `1`–`3` are UI over verbs that already exist (`set_device_patch`,
  `clear_device_patch`, `retry_fleet_patch`). If a stitch needs a new wire verb,
  stop and re-read.
- `1`–`3` touch the same code (`patchDiagnostics`, `fleetPatchPanel` in
  `dashboard.js`), so work them in order.
- **Bob gate:** before `2`, show Bob the Device page patch section (current and
  proposed, screenshotted from the running app) and get rulings on button names
  and whether push and pin are one control or two.
