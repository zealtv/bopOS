# 3-push-target-legibility

**Status:** waits on `66-projects/0-project-design` · re-scope before claiming
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

## After `66/0`

If per-device targets go away with pinning, the silent re-aim may vanish with
them. Whatever survives must show ineligible devices with a reason (`offline`,
`unassigned`, `simulated`) and never change a push's target without saying so.
Tests assert on the reason text, not option counts.
