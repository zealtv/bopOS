# Proposed repairs

Proposals only; no loom lifecycle mutations. All are bounded repairs using the
existing UI and wire vocabulary. F5/F6 share a repair because their cause and
verification both involve rebinding after generator row edits.

## cancel-detached-command-holds

- **Parent thread:** `67-repair-pass`
- **Goal:** prevent Remote reboot/shutdown/update holds from sending after a
  render replaces their button or their card is destroyed (F1, High).
- **Done when:** a short press followed by a heartbeat render and release sends
  nothing; pointer cancellation, leaving the target and card removal cancel
  outstanding holds; a full intentional hold sends once. Pending timers are
  cleaned at component lifetime. Browser regression and fast tier pass.

## reset-module-readiness-on-reconnect

- **Parent thread:** `67-repair-pass`
- **Goal:** keep simulated module controls inert until their current session's
  values are available, including reconnect and held-pad cleanup (F2).
- **Done when:** disconnect/reconnect before a fresh snapshot/sample cannot
  enable a null-valued slider or throw during drive/release; fresh valid data
  restores usable controls; stale session data does not restore readiness.
  Editor-input journey, bounded race regression and fast tier pass.

## reconcile-editor-live-module-panels

- **Parent thread:** `67-repair-pass`
- **Goal:** reflect the selected live input device's current module inventory,
  including the first report arriving after selection (F3).
- **Done when:** late discovered modules get panels; removed modules and changed
  types reconcile their panels/capture names; unrelated manual panels survive;
  unchanged reports preserve ongoing interaction. Module/editor journeys,
  late-report regression and fast tier pass.

## clear-spatial-cancelled-drags

- **Parent thread:** `67-repair-pass`
- **Goal:** release normal-map and editor-map gesture state when pointer input
  is cancelled or capture is lost (F4).
- **Done when:** seat, point, listener and editor-point gestures leave
  Spatial.dragging false after cancellation; subsequent state renders and new
  gestures work; cancelled clicks do not trigger double-click element edits.
  Normal pointerup still applies its final edit. Browser regressions and fast
  tier pass. Record separately whether any physical touchscreen was tested.

## bind-generator-drawers-once

- **Parent thread:** `67-repair-pass`
- **Goal:** make generator structural edits preserve valid segment removal
  controls without multiplying event listeners on surviving drawers (F5/F6).
- **Done when:** Add enables removal where appropriate; deleting rows never
  leaves an empty generator; remaining buttons reflect the current lower bound;
  repeated row/kind edits keep listener counts stable on surviving elements
  and leave sibling drawers alone. Drafts, focus, previews and Apply/Stop still
  work. Shared-control journey, edit regressions and fast tier pass.

## dispose-target-picker-subscriptions

- **Parent thread:** `67-repair-pass`
- **Goal:** release picker subscriptions and retained host closures when a
  Control card is removed (F7).
- **Done when:** followFocusSeat false installs no unnecessary storage listener;
  any installed listener is removed on picker/card destruction; repeated
  add/remove operations return global subscriptions to baseline; live focus
  following still works if retained. Control/picker regression and fast pass.
