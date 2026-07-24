# 6-control-tab-rename-design (thread 37)

The **Dashboard → Control** tab rename and its content: a target filter
(all / groups / seat), the cues / master / presets placement, and the
cue-section shrink. Part of the widened thread-37 scope deferred by the tied
first-bite design.

## Bob-gated design (user-facing Dashboard IA)

Output is a **written HTML proposal with mockups**
(`proposal-control-tab-rename.html` in this stitch), ratified by Bob before
implementation. Ends `.waiting` after the proposal lands.

## What the proposal must settle

- The rename itself (which tab, current label → "Control") and why the current
  IA under-names what the tab does.
- The in-tab target filter (all / groups / seat) and how it relates to the
  existing live-control scoping.
- Placement of cues / master / presets on the renamed tab and the cue-section
  shrink; where the shared control-surface component (stitch 5) sits.
- Interaction with presets (`41`) which will host their save/load UI here —
  name the seam; preset architecture stays 41's design.
