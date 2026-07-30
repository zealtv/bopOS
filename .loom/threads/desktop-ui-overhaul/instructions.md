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
`01-control-panel` (full-manifest visibility, then the mockup-driven design
pass and its implementation) is **tied**.

Restructured again 2026-07-30 (lore `2026-07-30-ui-unification-braindump`):
Bob reversed the rollout order. `02-app-wide-rollout-design` is **dropped** —
it would have ratified a token/pattern system top-down before the second
consumer of each pattern existed. Its replacement is `02-component-unification`:
identify the reusable components, design them one at a time, integrate each
into **every** consumer, and extract the coherent design language from what
shipped. The inventory (`.notes/component-inventory-2026-07.md`) is complete;
its ranked ledger and dependency graph lay out that stitch's children.

Added 2026-07-27 from the second braindump (lore
`2026-07-27-events-cues-and-global-controls-braindump`):
`03-global-controls-monitor` — master fader, MUTE ALL, and cue lead time
relocate to a panel in the Monitor dock (ratified direction, try it first).
Slot it after the control-panel implementation children; coordinate with
`02` since both touch app chrome.
