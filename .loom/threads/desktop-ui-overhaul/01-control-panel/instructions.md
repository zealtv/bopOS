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

Constraint from the same session: the system currently works and must keep
working — evolve the existing shared `ControlSurface`, don't fork it.
