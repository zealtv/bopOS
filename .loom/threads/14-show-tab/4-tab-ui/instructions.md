# 4-tab-ui

The Show tab itself. Requires stitches 1–3.

Scope:

- Rename the reserved "Sequencer" tab to **Show** (`static/index.html`,
  `TAB_NAMES` in `static/js/dashboard.js`, any tab-key references). Internal
  key `show`.
- One-column, many-row table of steps; dividers render as slim empty rows;
  sections are visually legible (subtle banding or divider styling). Don't
  hard-code single-column assumptions into the DOM/data flow more than
  needed.
- Each step row: trigger/state button (shows stopped/playing/paused;
  click-to-start; affordances for stop, pause, trigger-next per the design
  note), step alias, its messages as pills (alias or address short-form),
  duration and play-count summary, then-action summary.
- Focus model: clicking a step or a message pill focuses it (single focus,
  visible highlight) and will drive the stitch-5 inspector; this stitch
  lands the focus state and an empty inspector shell.
- Global transport strip: stop-all plus a what's-playing indicator (keep it
  minimal; per-step controls are primary).
- Live playback state from the stitch-3 WS broadcasts: state buttons and
  remaining-time indication update without reload.
- Match existing dashboard styling/idioms (`style.css`, existing tab JS
  patterns); touch-friendly per prior UX rulings.

Verify: `verify_show_tab.py`, Playwright headless per the house pattern
(copy the newest tied `verify_*.py` as template). Cover: tab renamed and
reachable, steps/dividers/pills render from a seeded show file, trigger
button starts a step and reflects live state, stop-all works, focus
highlight on step and pill. Remember the three Playwright gotchas in
CLAUDE.md.
