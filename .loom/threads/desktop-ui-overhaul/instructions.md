# desktop-ui-overhaul

Overhaul the web application so it reads and works like a purpose-built
desktop tool: smaller controls, tighter padding and gaps, clearer information
hierarchy, and substantially less unused space.

This is app-wide desktop design work, not a Show-only style pass. Reuse the
existing palette and theme system, and preserve the facilitator surface's
separate tablet-first requirements. Existing behavior and accessibility remain
constraints; density should improve scanning and working area without making
controls ambiguous or keyboard interaction fragile.

Restructured 2026-07-27 (lore
`2026-07-27-control-panel-ui-and-architecture-braindump`): Bob mocked up the
compact control-panel UI and wants it built first as the reference surface.
Order: `01-control-panel` (full-manifest visibility, then the mockup-driven
design pass and its implementation) → `02-app-wide-rollout-design` (extract
the language, propose the app-wide rollout, split implementation into
coherent tab/surface slices after Bob ratifies the direction).
