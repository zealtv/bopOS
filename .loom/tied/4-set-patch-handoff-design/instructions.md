# 4-set-patch-handoff-design (thread 37)

The Device-tab **"Set patch…"** hand-off: from a selected device on the Device
tab, jump to the Patches/Control-tab target picker pre-scoped to that device, so
an operator working a single node (Ciro Toast) doesn't hunt for it in a fleet
picker. Part of the widened thread-37 scope deferred by the tied first-bite
design.

## Bob-gated design (user-facing Dashboard IA)

Output is a **written HTML proposal with mockups**
(`proposal-set-patch-handoff.html` in this stitch), ratified by Bob before
implementation. Ends `.waiting` after the proposal lands.

## What the proposal must settle

- The affordance on the Device-tab detail (button copy, placement near patch
  diagnostics) and what "pre-scoped" means when the target picker lives on the
  Patches/Control tab.
- Tab switch vs in-place mini-picker on the Device tab — reversibility and where
  the pin confirm happens.
- **The seatless-control reality (from bite 2's design note):** OSC v1.5 targets
  content by seat, so pinning needs a seat binding. The hand-off is where a
  "standalone" unbound device (Ciro Toast) is offered a one-click bind-to-own-seat
  so control is not gated on the operator understanding seats. Settle this UX.
- Consistency with the "do not gate independent control on being seatless"
  advice while respecting the wire constraint.
