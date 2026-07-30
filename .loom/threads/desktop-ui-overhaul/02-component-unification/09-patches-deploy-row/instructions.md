# 09-patches-deploy-row

Put the fleet-patch deployment controls on one line.

`index.html:83` stacks `.fleet-patch-choice` (patch `<select>` above target
`<select>`) over `.fleet-patch-actions` (`Deploy as fleet patch`, `Revert`).

Bob, 2026-07-30: *"it would make a lot more sense for those to be side by side
so that the patch, the target, and the buttons are all in a single line."*

Needs `07-target-selector-component`'s **device**-domain picker — this target
selects physical devices, not seats. Bob was unsure the picker is the right
object here; if the single-line layout reads better with a plain `<select>`,
say so with evidence rather than forcing the component in.

Small once `07` exists. Also sweep the rest of the Patches tab for the same
class of awkward stacking now that manifest entries are drag-reorderable.
