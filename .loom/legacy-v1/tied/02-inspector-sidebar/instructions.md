# 02-inspector-sidebar

Give the Show inspector its own space as a collapsible sidebar so its
height can never move the OSC terminals again. The core behavior is
ratified by the braindump (lore `2026-07-20-show-chrome-density-braindump`);
the review gate `01` is paused (lanes dependency), so settle the interaction
details (affordance placement, expanded width, hidden-state focus behavior,
collapsed-state rendering) in this stitch: propose defaults and put the
genuinely contestable ones to Bob before building past them.

## Outcome

- The inspector column becomes a collapsible sidebar with a stable footprint:
  expanding/collapsing it, or the inspector's own content growing (message
  builder, target picker, then-actions), must never push the OSC terminals
  or the step list out of view. Tall inspector content scrolls within the
  sidebar.
- Expanded: the current step/divider/message inspector renders as today
  (post-`show-layout-polish`: inline-editable step name as the title).
  Collapsed: the step list and terminals reclaim the width.
- Workflow per Bob: popped out while building a show, hidden while running
  one — so the toggle must be quick, obvious, and keyboard-accessible, and
  the chosen state should survive re-renders (persistence scope per the
  ratified decisions).
- Desktop-first. Keep the current narrow/mobile behavior working (generally
  fine sizewise today); don't regress the 768px layout or the responsive
  terminal stacking from `03-responsive-osc-terminals`.
- Preserve all existing inspector functionality: focus-driven switching,
  message builder, wire preview, pill copy/paste interplay, undo, and the
  two-element UI guard.

## Verification

Focused Playwright (copy conventions from
`.loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py`): terminals
keep their viewport position while the inspector grows (drive a message
inspector with many args/then-actions); collapse/expand round-trip restores
state; focus changes while collapsed behave per the ratified decision;
1280px + 768px; light/dark; no page-level horizontal overflow. Re-run the
tied edit-bar and OSC-terminal suites unmodified. Retain screenshots.
