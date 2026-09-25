# 1-device-push-action

**Status:** ready · ends with a Bob gate
**Goal:** a push button on the Device page, always shown, enabled whenever the
device can receive a patch — not only when the badge shows a fault.

No new wire verb needed.

## Today

In `patchDiagnostics` (`dashboard.js`):

```js
const remediation=allowRemediation&&d.online&&["missing","stale","stale_unverified","mismatch","failed","timeout"].includes(d.patch_badge)
  ? `<button id="fleet-patch-retry">Sync to ${d.patch_pinned?'pinned':'fleet'} patch</button>`:"";
```

It sends `retry_fleet_patch`, which already pushes the device's pin (or the
fleet patch if unpinned). Problems:

- hidden when the badge reads `current` — which is most of the time;
- named after the mechanism ("Sync"), not the intent (Bob says "update patch");
- sits among remediation buttons, so it reads as a repair action.

## Change

- Always render a push action in Patch diagnostics. Enabled when seat-bound,
  online and non-virtual; otherwise disabled with a `title` reason (`3` owns the
  visible sentence).
- It sends `retry_fleet_patch` — pushes the **effective desired patch** shown in
  the `Desired patch` row. No patch picker; choosing is the Patch tab's job.
- Keep `allowRemediation` (seat-bound check) — unbound targeting isn't possible
  in OSC v1.5.
- Pushing restarts the engine → confirm, matching neighbouring confirms.
- Fold the old badge-conditional button into this one if it reads better; that's
  part of the proposal.

## Done when

Extend `tests/verify_device_patch_targeting.py`:

- online, seat-bound device with badge `current` has an enabled push (fails
  today);
- pressing it sends `retry_fleet_patch` with that uid;
- offline device shows it disabled, not absent.

Hardware: a push from the Device page to a rig device end to end. State in
`verification.md` which half ran.

## Bob gate (before `2` starts)

Screenshot the Device page patch section as-is and as proposed (generate from
the running app — `mockup.py` in `08/1-columns-design` is the pattern) and ask:

1. Push and pin: one control or two?
2. "Update patch" or "Push patch"?

Pinning is due for a refactor soon (Bob, 2026-09-25) — check its state before
designing `2`, and keep this stitch's changes easy to fold into it.
