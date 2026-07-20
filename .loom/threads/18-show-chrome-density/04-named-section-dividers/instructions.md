# 04-named-section-dividers

Dividers mark sections, so sections can be named: give dividers a name and
the mockup's presentation — the name centred with horizontal lines either
side (see `.loom/tied/01-layout-review/wireframes.html` and lore
`2026-07-20-show-chrome-density-braindump`).

## Outcome

- Additive `alias` field on divider items in the show document
  (`dashboard/show_model.py`), defaulting to null/untitled; persistence,
  undo, duplicate (fresh UID, alias copied), and second-client broadcast
  behave like step aliases.
- Divider row renders the name with the lines-either-side styling in both
  themes; unnamed dividers render a plain rule (current look). `01` is
  paused, so decide the editing surface in-stitch (default proposal: inline
  on the row matching step-name behavior, plus a name field in the currently
  empty divider inspector; confirm with Bob if deviating).
- Long names truncate/ellipsize without widening the page; dividers stay
  drag-reorderable and selectable exactly as today.

## Verification

Focused Playwright: naming via the ratified surface(s) (commit/cancel/blank
semantics matching step names); persistence + second-client; duplicate
copies the alias with a fresh UID; themed rendering with lines either side;
truncation at narrow width; drag/selection regressions; no horizontal
overflow. Re-run the tied edit-bar suite unmodified. Retain screenshots.
