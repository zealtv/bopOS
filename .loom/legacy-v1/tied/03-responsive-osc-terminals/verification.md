# Verification — 03-responsive-osc-terminals

## What changed

`dashboard/static/css/style.css` (single-line minified block containing the
`#show-consoles` / `.show-console*` rules):

- `#show-consoles`: `grid-template-columns:repeat(2,minmax(0,1fr))` (was a
  single implicit column) plus `align-items:start`, with a
  `@media(max-width:899px){#show-consoles{grid-template-columns:minmax(0,1fr)}}`
  override — two equal-width columns at viewport width >= 900px (the
  ratified breakpoint), stacking single-column below it. Outgoing renders
  before incoming in source order (unchanged from `show.js`), so stacking
  naturally puts outgoing above incoming. `minmax(0,1fr)` keeps a long
  `white-space:pre` OSC line from blowing out the grid track.
- `.show-console`: `display:flex;flex-direction:column;transition:none`
  (was a plain block `<details>`). `transition:none` neutralizes Chromium's
  built-in `<details>` open/close transition, which otherwise left a stale
  computed height on the element after toggling closed (see gotcha below).
- `.show-console[open]{height:320px}` — the ratified fixed expanded height
  (~12 monospace log lines). Only applies while open; closed panels fall
  back to their natural (summary-only) height.
- `.show-console[open]::details-content{display:contents}` — see "gotcha"
  below; without this the log never actually clips to 320px.
- `.show-console summary` / `.show-console-bar`: `flex:none` added so they
  keep their natural size and don't get squeezed by the flexed log.
- `.show-console-log`: `flex:1 1 auto;min-height:0` replaces the old
  `max-height:240px`, so the log fills whatever vertical space remains
  inside the fixed 320px panel after the summary and filter/action bar,
  and scrolls internally (`overflow:auto`, unchanged) rather than growing
  the panel.

No changes to `dashboard/static/js/show.js` — the JS already builds
outgoing-then-incoming in that order, defaults both panels closed, and all
filter/pause/clear/count/auto-scroll logic was already correct; only the
CSS needed to change for this stitch.

### A genuine Chromium `<details>` layout gotcha (worth recording)

Modern Chromium (this repo's Playwright pins 149.x) renders everything
inside a `<details>` except `<summary>` inside an internal
`::details-content` anonymous box used for its native open/close
animation. Setting `display:flex` directly on the `<details>` element does
**not** make its light-DOM children (`<summary>`, `.show-console-bar`,
`.show-console-log`) into real flex items — only `<summary>` and the single
`::details-content` wrapper are actual flex items, and that wrapper sizes
itself to its own content, so a fixed height on the `<details>` had no
effect on the log's growth. Fix: `.show-console[open]::details-content
{display:contents}` unwraps the pseudo-box only while open, promoting the
bar and log to real flex items so `flex:1 1 auto;min-height:0` on the log
can actually clip it to the remaining space. (Left unscoped to `[open]`,
this rule also fights the UA's `:not([open])` content-hiding logic and
made *closed* panels render at full height — the scoped `[open]` selector
avoids that.)

A second, unrelated gotcha: CSS Grid's default `align-items:stretch` made
a *closed* (summary-height) panel stretch to match its *open* (320px)
sibling in the same grid row, since both columns share one implicit row.
Fixed with `align-items:start` on `#show-consoles`, which is also required
for "collapsed terminals remain summary-height and expand independently."

## Commands run

```
~/.venvs/bopos/bin/python .loom/threads/show-layout-polish/03-responsive-osc-terminals.stitching/verify_osc_terminals.py
~/.venvs/bopos/bin/python .loom/tied/7-osc-consoles/verify_show_consoles.py
~/.venvs/bopos/bin/python .loom/tied/5b-compact-rows/verify_show_compact.py
~/.venvs/bopos/bin/python .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
```

## Results

- `verify_osc_terminals.py` (new, in this stitch dir): **29/29 checks PASS**.
  Covers: equal top y-coordinate and equal ~320px height for both expanded
  panels at 1280px; two-column layout with equal widths at 1280px and at
  the 1024px tablet width (both >= the 900px breakpoint); outgoing-above-
  incoming stacking and full container width at 768px (below the
  breakpoint); panel height unchanged after driving sustained live traffic
  (simfleet heartbeats + repeated step triggers) through both consoles;
  independent internal log scrolling (scrolling one log to top doesn't
  move the other, and doesn't scroll the page); independent collapse/
  expand (collapsing outgoing leaves incoming open at full height, and the
  collapsed panel shrinks to summary height); filter (wildcard + `!`
  negation), pause/resume, clear/refill, and count-summary all retained;
  default auto-scroll-to-bottom retained; a very long (400+ char) OSC
  string frame causes no page-level horizontal overflow and doesn't change
  panel geometry; light and dark themes both render the console log with
  distinct, theme-appropriate background/text colors (screenshots below);
  zero page errors across all viewport widths.
- `.loom/tied/7-osc-consoles/verify_show_consoles.py` (original OSC console
  suite, re-run unmodified): **10/10 PASS** — no regression.
- `.loom/tied/5b-compact-rows/verify_show_compact.py` (Show dense-layout
  suite, re-run unmodified): **12/12 PASS** — no regression.
- `.loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py` (the
  stitch this one builds directly on top of, re-run unmodified):
  **51/51 PASS** — no regression from the CSS-only change.

## Screenshots (retained in this stitch dir)

- `review-1280-dark.png` — 1280px desktop, dark theme, both consoles
  expanded side by side at equal height, live traffic visible in both.
- `review-1280-light.png` — 1280px desktop, light theme, same expanded
  layout (contrast check).
- `review-768-stacked.png` — 768px narrow, both consoles expanded,
  outgoing stacked above incoming, each full width.

## Deviations from the brief

None. Breakpoint (900px viewport width), fixed expanded height (~320px),
column layout, and outgoing-then-incoming stacking order all match
`.loom/tied/01-layout-review/decisions.md` exactly.

## Unverified / boundaries

- Real hardware/browser engines other than the Playwright-pinned Chromium
  were not exercised; the `::details-content` behavior is Chromium-
  specific to recent versions (this repo's Playwright chromium is 149.x).
  Older Chromium/other engines without a `::details-content` pseudo simply
  ignore that selector (no-op), which degrades to the pre-fix behavior
  (log not clipped to 320px) rather than breaking outright — worth a note
  if bopOS ever needs to support a materially older embedded Chromium.
  Firefox/Safari were not tested; the dashboard's supported target has
  been Chromium-family throughout this project per prior stitches.
  Nothing here needs Bob's attention — it's within the stitch's normal
  automated-verification boundary.
