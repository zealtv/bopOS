# 5-live-control-placement-design (thread 37)

The **per-device live-control panel** and the reusable **control-surface
component** behind it: today the `dashboard:true` manifest-driven promoted
controls render for All/Group/Seat. This designs (a) one shared component and
(b) its placement + shape when hosted on the Device tab, scoped to a single
device's current patch. Part of the widened thread-37 scope deferred by the tied
first-bite design.

## Bob-gated design (user-facing Dashboard IA)

Output is a **written HTML proposal with mockups**
(`proposal-live-control-placement.html` in this stitch), ratified by Bob before
implementation. Ends `.waiting` after the proposal lands.

## What the proposal must settle

- The one control-surface component and its three hosts (patch editor, Device
  tab, Control tab) — inputs/outputs, so it isn't authored three times.
- Placement + shape of the per-device panel on the Device tab (relative to
  patch diagnostics, enabled state, audio config). Expect it to subsume the old
  Seats-detail vertical-overflow complaint — don't patch that separately.
- How a per-device panel reflects a pinned vs fleet patch (thread 37 bite 2)
  and hosts precision entry (thread 40) + the generator affordance (stitch 3).
- Reuse of the editor param-tree renderer; nested-identity controls intact.
