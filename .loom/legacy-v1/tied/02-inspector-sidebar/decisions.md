# 02-inspector-sidebar — decisions

## Ruled by Bob (2026-07-21, in-session before the autopilot run)

- **Hidden-state focus behavior: expand on double-click only.** Single
  click/tap on a step row, divider row, or message pill selects silently
  (focus state updates; the collapsed sidebar stays collapsed). Double-click
  (or Enter on a focused item) expands the sidebar showing that item's
  inspector. Rationale: matches the "hidden while running a show" workflow —
  stray clicks during a run never pop the inspector open, but there is still
  a fast pointer path to open it on a specific item.
- **Persistence: session only.** The expanded/collapsed state lives in
  module state in `show.js` — it survives every re-render (heartbeats,
  document broadcasts, focus changes) but resets to **expanded** on page
  reload. Not localStorage, not the show document.

## Proposed defaults (orchestrator, per the stitch's mandate to settle
## non-contestable details in-stitch)

- **Affordance placement:** the toggle lives on the sidebar itself. Expanded:
  an icon button in the inspector header row (top-right), `aria-expanded`,
  labelled "Hide inspector". Collapsed: the sidebar renders as a narrow
  vertical rail (~40px) that is one big button — vertical "Inspector" label,
  full height, keyboard-focusable, labelled "Show inspector". One obvious
  click either way; both in the tab order.
- **Expanded width:** 300px, unchanged from today.
- **Collapsed rendering:** 40px rail; the step list and (indirectly) the
  consoles reclaim the width via the workspace grid.
- **Footprint stability mechanism:** the sidebar is taken out of the
  document-height equation — the workspace row's height is driven by the
  step-list shell only, and the inspector panel is viewport-capped with
  internal scroll (`overflow-y: auto`). Growth of inspector content
  (message builder, target roster, then-actions) can never move the
  consoles or the step list.
- **Mobile (≤1020px single-column) behavior:** unchanged layout (inspector
  below the list, static). The toggle still works; collapsed renders as a
  slim horizontal "Inspector" bar. 768px layout and console stacking from
  `03-responsive-osc-terminals` must not regress.
