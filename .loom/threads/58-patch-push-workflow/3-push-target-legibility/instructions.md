# 3-push-target-legibility

**Status:** ready
**Goal:** when a device can't receive a patch, say why — don't silently drop it
from the list.

## Today

- **Patches tab** (`fleetPatchPanel`, `dashboard.js`): targets are
  seat-bound ∧ online ∧ non-virtual. Anything else is simply missing. Worse, if
  the selected device drops out, the selection **silently resets to "Whole
  fleet"** — the next press deploys everywhere.
- **Device tab:** the unbound case is explained well (`unboundNote` — use its
  voice). Offline just removes the buttons with no explanation.

This is why Bob concluded "pin to device won't push": Ciro Toast wasn't in the
list.

## Change

- **List ineligible devices as disabled options with a reason** (`offline`,
  `unassigned`, `simulated`). Don't mount `TargetPicker` here — `09` ruled it too
  tall for this row.
- **Never silently re-aim.** If the selected target becomes ineligible, keep it
  and disable the button with the reason, or show the reset visibly.
- **Device page says why it can't push** (offline, virtual, unbound), next to
  `1`'s disabled button.

## Done when

Extend `tests/verify_device_patch_targeting.py`, asserting on the **reason
text**, not just option counts. For an offline device, prefer driving state
directly; if you must kill simfleet, the offline sweep takes 30 s (gotcha 14).
