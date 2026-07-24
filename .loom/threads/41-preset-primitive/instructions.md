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
