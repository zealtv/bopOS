# 3-push-target-legibility

**Status:** after `66-projects/1-remove-device-pins` · re-scoped 2026-10-04
**Goal:** when a device can't receive a patch, say why — never silently drop it
from the target list or re-aim a push.

## Today

- **Patches tab** (`fleetPatchPanel`, `dashboard.js`): only seat-bound, online,
  real devices are listed. If the selected device drops out, the selection
  **silently resets to "Whole fleet"** — the next press deploys everywhere.
  That last part is a real hazard.
- **Device tab:** the unbound case is explained well (`unboundNote` — use its
  voice); offline just loses the buttons.

This is why Bob concluded "pin to device won't push": Ciro Toast wasn't in the
list.

## Re-scoped from the ratified projects design (2026-10-04)

`66/1` removes the per-device target picker, so the silent re-aim goes with
it — confirm that, then this is about the whole-fleet push saying who won't
get it. Whatever survives must show ineligible devices with a reason (`offline`,
`unassigned`, `simulated`) and never change a push's target without saying so.
Tests assert on the reason text, not option counts.
