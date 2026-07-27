# 41-preset-primitive

Re-found presets as a manifest-scoped primitive. From Bob's 2026-07-24
patching-session braindump (lore `2026-07-24-patching-session-braindump`),
extended same-day in conversation with the Show-tab trigger + interpolation
idea.

The vision: a preset belongs to a patch and its manifest and applies to a
single device/seat. Collections of presets compose onto groups/seats/all.
Save a preset from the patch editor's control panel while sculpting the
patch; load it from the Control tab onto a seat, a group, or everything.
Trigger presets from the Show tab as sequenced actions — and, powerfully,
**interpolate into a preset over time**: an optional duration + curve, so a
show step can morph the fleet's state rather than snap it.

Today's dashboard presets are dashboard-side parameter snapshots; this
thread moves preset identity into the patch/manifest layer. Bob explicitly
asked for an architectural evaluation, not a straight port.

Child `1-preset-architecture-design` is the Bob-gated design stitch;
implementation stitches follow ratification.

**Gated 2026-07-27 on `entity-architecture-review`** (lore
`2026-07-27-control-panel-ui-and-architecture-braindump`): Bob wants the
holistic entity/coupling review (devices, seats, patches, presets, shows)
done before the preset design is written, so the preset primitive lands on a
reviewed model instead of adding to the complexity smell. The mockup's
provisional preset row (dropdown + new/save/del at the control-panel top) is
UI input for the design stitch.
