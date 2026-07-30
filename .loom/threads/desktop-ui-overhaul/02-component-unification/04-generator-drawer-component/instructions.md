# 04-generator-drawer-component

Lift the generator drawer's chrome out of `control-surface.js` so the Show
inspector renders the identical component.

The *fields* are already shared: `js/param-generator.js` exports `fields()`,
`preview()`, `segmentRow()`, `unitOptions()`, and both hosts call them. Only
the chrome diverges:

- `control-surface.js:231` `generatorDrawer()` — the ratified drawer:
  `LFO | loop | fade` latching tabs, `--subpanel` face, 12px indent, pointer
  up to the ∿ icon, `--mod-soft` active tab.
- `show.js:786-789` — the same fields in a bare `<label>generator <select>`
  stack inside `.show-inspector-section`, with a plain option list
  (value/fade/loop/lfo/stop).

Bob, 2026-07-30: the Show inspector *"should be using the control panel …
or the LFO modulation panel where that's appropriate"*, and the inspector's
narrow column is exactly the shape the drawer was designed for.

Work:

- Move the drawer chrome into `param-generator.js` (or a sibling module) so
  both hosts share tabs, face, indent and pointer.
- The Show inspector adopts it. Its `value` and `stop` modes have no
  equivalent in the panel's three tabs — resolve that explicitly rather than
  quietly dropping either.
- The drawer has a fixed width and **must not reflow** (Bob, 2026-07-30);
  that width sets the minimum width of any host. Coordinate with `06`, which
  owns the reflow rules.
- Open-drawer and draft state must keep surviving the heartbeat re-render
  (`openDrawers` / `drafts` live outside the DOM for this reason).

Verify: `tests/verify_live_param_kinds.py` and the Show generator journeys.
Watch CLAUDE.md Playwright gotcha 10 — changing the inspector's generator
`<select>` persists new args onto the focused message, so use one fixture
message per generator kind rather than switching kinds in-test.
