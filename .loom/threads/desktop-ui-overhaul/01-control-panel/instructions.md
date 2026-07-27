# 01-control-panel

Make the Control tab's control panel the reference implementation of the new
compact desktop UI language, per Bob's 2026-07-27 mockup and braindump (lore
`2026-07-27-control-panel-ui-and-architecture-braindump`). Get this one
surface really nice first; `02-app-wide-rollout-design` then extracts the
rules and pushes them across the application — same pattern as the tied
Show-tab chrome pass.

Two children, in order: `1-full-manifest-visibility` (a small ratified
behavior change, shippable now) then `2-control-panel-design` (the
mockup-driven design pass; Bob ratifies before implementation children are
laid out).

Added 2026-07-27 from the second braindump (lore
`2026-07-27-events-cues-and-global-controls-braindump`):
`8-manifest-reorder` — drag-reorder manifest entries in the Patch tab so the
control panel can be reordered. Independent of the event plane; workable
after `7-preset-slot`. The same braindump rules that the panel will grow
separate parameters/events sections (that lands with `44-event-plane`) and
relocates the global controls (`../03-global-controls-monitor`).

Constraint from the same session: the system currently works and must keep
working — evolve the existing shared `ControlSurface`, don't fork it.
