# 11-set-patch-handoff — done

A **Set patch…** button in the Device tab's patch diagnostics hands off to the
Patches-tab picker, pre-scoped to that device, with a one-click Seat for an
unbound one.

## What shipped

- **Set patch…** sits with the other patch-diagnostics actions (beside "Sync
  to…" / "Follow fleet patch"), disabled offline and absent for virtual
  devices.
- **Bound device:** sets `fleetPatchTarget` to the uid and switches to the
  Patches tab. The shipped bite-2 picker does not move and is not duplicated —
  the verifier asserts there is still exactly one `#patch-target` in the app.
- **Unbound device:** one confirm explains that targeting one device addresses
  it by Seat, then `add_seat` + `bind_seat` give it an **ordinary** Seat named
  after the device. The binding is asynchronous, so the hand-off is held in
  `pendingPatchHandoff` and completed by `resumePatchHandoff()` when the next
  state shows the device bound.
- **A way back:** a crumb on the Patches tab reads "← Back to <device>" and
  returns to the Devices tab with that device selected. That answers the
  argument for the mini-picker Bob rejected — losing the device context.

## Bug the verifier caught

The crumb's handler was first written inside `renderFleetPatch`, where
`const select = $("#patch-select")` **shadows the global `select(uid)`**. The
click threw `select is not a function`, so "back" silently did nothing. Moved
to its own `renderPatchHandoffCrumb()` with a comment saying why it lives
apart — the shadowing is not obvious and would be re-introduced by anyone
folding it back in.

## Terminology held

"Pinned" still means patch-pinned only. Two checks defend it: binding a Seat
does **not** set `patch_pinned`, and pinning a patch is what does. A seat-bound
standalone device gets no second sense of the word.

## Verification

- **`tests/verify_set_patch_handoff.py` — new, 14/14 green.** The button; the
  hand-off lands on Patches (and not Control) with the target pre-selected and
  the confirm reading "Pin to device"; one picker only; the crumb names the
  device and returns to it; an unbound device gets a Seat in one click and the
  hand-off completes when the binding lands; the Seat is ordinary (integer id,
  no hidden/utility flags); and the two "pinned" checks above.
- Full suite green: `verify_device_patch_targeting` 14/14, `verify_control_tab`
  15/15, `verify_device_control_panel` 12/12,
  `verify_control_surface_component` 11/11, `verify_generator_drawer` 38/38,
  `verify_live_param_checkbox` 10/10, `verify_precision_param_input` 13/13, and
  all 14 `tests/test_*.py` unit suites.
