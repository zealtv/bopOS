# desktop-ui-overhaul

Overhaul the web application so it reads and works like a purpose-built
desktop tool: smaller controls, tighter padding and gaps, clearer information
hierarchy, and substantially less unused space.

This is app-wide desktop design work, not a Show-only style pass. Reuse the
existing palette and theme system, and preserve the facilitator surface's
separate tablet-first requirements. Existing behavior and accessibility remain
constraints; density should improve scanning and working area without making
controls ambiguous or keyboard interaction fragile.

Start with `01-density-and-layout-design`, then split implementation into
coherent tab/surface slices after Bob ratifies the direction.
