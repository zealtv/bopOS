# 05-compact-chrome — decisions

## Ruled by Bob (2026-07-21, before the autopilot run)

- **Scope: Show tab only.** The facilitator tab is excluded (standing).
  A follow-up stitch is to be laid on the thread to assess extending the
  chrome to the rest of the app, or whether to stage adoption — Bob's
  words: "show tab only — leave a stitch to assess doing the rest of the
  app or whether to stage adoption."

## Concrete values (orchestrator proposal — Bob was asleep; derived from
## the `01-layout-review` wireframe he ratified the direction of, which
## uses 3–4px radii, 4×8px paddings, 10–12px type. Easy to re-tune: all
## expressed through shared variables, one place to change.)

New `:root` variables (theme-independent, global-ready but consumed only
by Show-tab rules this stitch):

- `--chrome-radius-panel: 6px` (panels/consoles; was 9px)
- `--chrome-radius-control: 4px` (buttons, inputs, selects, rows; was 5–7px)
- `--chrome-radius-small: 3px` (pills, chips, tiny controls; was 5–6px+)
- `--chrome-control-height: 32px` (standard control min-height; was 44px)
- `--chrome-control-pad: 4px 8px` (button padding; was ~6px 12px / 9px)
- `--chrome-panel-pad: 12px` (panel padding; was 16px)
- `--chrome-gap: 12px` (workspace/console gaps; was 18px)

Touch safety: visual control boxes shrink, but every touch-relevant
control keeps an effective ≥44px hit target via the existing house
pattern (`::after{content:"";position:absolute;inset:-Npx}`), extended
where the shrink would otherwise drop below 44px. Keyboard
`:focus-visible` outlines retained everywhere the chrome changes.

Bounded step list: the `p4` scrollbox stays the bound; with the tighter
chrome its edge must read clearly (visible border on the scrollbox) and
the edit bar stays pinned above it.
