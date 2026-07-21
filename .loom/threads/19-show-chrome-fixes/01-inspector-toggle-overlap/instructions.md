# 01-inspector-toggle-overlap

**Defect (Bob, 2026-07-21):** "When the inspector is expanded in a narrow view,
its little closing button is overlapping the delete button in the toolbar."

The collapse toggle shipped with `18-show-chrome-density/02-inspector-sidebar`
(see `.loom/tied/02-inspector-sidebar/`); the edit bar shipped with
`show-layout-polish/01-layout-review`. At narrow widths the inspector panel
stacks under/over the edit bar and the two controls collide.

## Outcome

- At narrow widths, the expanded inspector's collapse toggle and the edit bar's
  delete button never overlap, at any inspector content height.
- The fix is a layout fix, not a z-index fix — one control on top of the other
  still means one is unreachable.
- Wide-viewport layout is unchanged.

## Verify

Playwright suite per `CLAUDE.md` ("Dashboard browser tests"), copying the
newest tied `verify_*.py` as the template. Assert non-intersecting bounding
rects for the two controls with the inspector open, gathering **all rects in a
single `page.evaluate`** (gotcha 9), at a narrow viewport and again at a wide
one. Cover both a short inspector (divider) and a tall one (message with an
LFO generator).
