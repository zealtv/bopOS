# 2-pin-unpin-toggle

**Status:** blocked on `1-device-push-action` (and Bob's ruling there)
**Goal:** one pin control on the Device page that shows and flips the state —
*"a simpler pin/unpin button to get the device to hold onto a patch"* (Bob).

## Today

The model is already clean: the server publishes `patch_pinned` and
`pinned_patch` separately from `patch_badge`, and `set_device_patch` /
`clear_device_patch` are symmetric. The UI isn't:

- **Pin** lives on the Patches tab, as the deploy button relabelled `Pin to
  device` when a device is selected.
- **Unpin** lives on the Device tab as `Follow fleet patch` (only when pinned and
  online).
- Current state is a 📌 with the explanation in a tooltip (`pinnedMarker`).

## Change

One control in the Device page's patch section: *pinned to `<patch>`* ⇄
*following fleet patch*. Pin → `set_device_patch` with the patch currently
shown as desired; unpin → `clear_device_patch`.

Two things to settle while building:

- **Pin means "hold what's running"** — no patch picker.
- **Pinning shouldn't restart the engine for no reason.** `set_device_patch`
  always re-converges. Add a server-side skip when the pin resolves to the same
  **fingerprint** the device already reports. Never skip on name alone — a
  skipped push that was needed is the worse failure.

Keep `Pin to device` on the Patches tab (pinning a *different* patch is a
deploy). Align the wording and note in `decisions.md` that both exist on
purpose.

## Done when

Extend `tests/verify_device_patch_targeting.py`:

- unpinned device shows "following fleet"; click → `set_device_patch`, state
  flips on next broadcast; click again → `clear_device_patch`;
- pin state survives reload;
- if the skip lands: same fingerprint → no engine restart; different → restart.

Gotcha 12: scope roster clicks to `#device-roster`.
