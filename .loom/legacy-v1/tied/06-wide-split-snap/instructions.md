# 06-wide-split-snap

The interaction and persistence rules are ratified in `01-dock-design`.

Bob: "In a narrow view, each of those views could be a tab on a single panel, but
in a wider view, we should be able to drag those tabs either side so that they
snap to the sides of that wider panel. Think console tabs in VS Code."

## Outcome

- At wide widths, a dock tab can be dragged to the left or right edge of the dock
  frame and dropped to occupy that side, splitting the dock into two panes.
- Drop targets are visibly indicated during the drag; an aborted drag restores
  the previous layout.
- Dragging the last tab out of a pane collapses that pane, restoring a single
  pane — no empty-pane state.
- Below the design's breakpoint, the dock is a single tabbed panel and the drag
  affordance is absent (not merely inert).
- Layout persists per `01`'s persistence ruling.
- Keyboard/accessible equivalent: the split must be reachable without a pointer
  drag (a tab context action is fine).

## Verify

Playwright: drag a tab to the right edge at a wide viewport, assert two panes
with the expected tab distribution and non-overlapping rects (gather rects in a
single `page.evaluate` — gotcha 9); shrink the viewport and assert the single-
panel fallback; reload and assert the layout persisted; drive the keyboard path.
