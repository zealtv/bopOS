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

**Architecture gate CLEARED 2026-07-27**: `entity-architecture-review` is
tied. The preset design proceeds on the ratified four-layer model — see
`.notes/entity-map-2026-07.md` (as-is map) and the tied
`2-workflows-and-simplification` proposal.md/decisions.md. Bob ratified
in-session: venue presets **retire** when this thread lands (store is empty,
no migration — settles Q8); collections start as **show steps / step
templates**, not a new store (reshapes Q5); shows will reference groups **by
name** and content by `{name, fingerprint}` with derived non-blocking drift
warnings (the drift policy of Q1/W5); one application path with hard
takeover is the global rule. The mockup's provisional preset row (dropdown +
new/save/del at the control-panel top) is UI input for the design stitch.
**Re-sequenced same day (Bob, 2026-07-27): `44-event-plane` comes first.**
The mockup braindump's event parameters (single/pair/triplet MIDI-style
events with forward synchronization, likely a `<target>/e/*` plane) and the
toggle/integer/enum kinds may need to exist before the preset design, since
a preset must know what it captures for each kind. The design stitch here
stays `.waiting` behind `desktop-ui-overhaul/01-control-panel` and
`44-event-plane/1-event-plane-design`.

**Additional design input (Bob, 2026-07-27): capture-as-step.** From the
Control tab, once presets are set up targeting different groups/seats, one
click stores the current target→preset arrangement as a **show step** — the
authoring path for "meta presets", closing the ratified "collections start
as show steps" ruling. The design stitch's Q6 (show integration) must cover
this capture flow: what exactly is snapshotted (the target→preset mapping;
current values for targets without a preset applied?), and where the button
lives (coordinate with the control-panel design's preset row).
