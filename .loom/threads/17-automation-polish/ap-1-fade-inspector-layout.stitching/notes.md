# ap-1 notes

## Diagnosis

The Show inspector is a fixed **300px** column on desktop
(`.show-workspace{grid-template-columns:minmax(0,1fr) 300px}`), while
`.show-param-segment` is a rigid 3-column grid whose only escape hatch
was a `@media (max-width:760px)` viewport query. So the overlap Bob
screenshotted is the *default desktop state*: the row needs ~340px and
the inspector's content box gives it ~240px; the uppercase labels
overflowed into each other ("DESTINATIONDURATION") and the duration
number input collapsed behind its unit select. The wide screenshot was
the <1020px stacked-workspace case, where the inspector is full width
and the 3 columns fit — which is why the bug looked width-dependent.

## Fix

Container query instead of viewport query (`style.css`):
`.show-inspector-shell` becomes an inline-size container
(`container-name:show-inspector`), and at container width ≤380px the
segment row and the LFO grid stack to one column. Desktop 300px column
→ stacks; full-width inspector (<1020px viewport) → keeps the compact
3-column row. The 760px viewport rule stays for phones. No JS or markup
changes.

## Verify

`verify_fade_inspector_layout.py` (house pattern: real server + simfleet
+ headless Chromium, repo-by-marker root, random loopback ports):

- desktop 1280px: inspector measures ~300px; destination/duration/unit/
  Remove boxes pairwise non-overlapping (single-scroll-state rects),
  inputs ≥40px usable width, labels non-overlapping, row stacked;
  LFO period input usable via the dedicated LFO fixture message.
- 960px viewport: full-width inspector keeps destination+duration on one
  row, still non-overlapping.
- No console errors. Screenshots: `inspector-narrow.png`,
  `inspector-wide.png`.

Run: `~/.venvs/bopos/bin/python verify_fade_inspector_layout.py` →
**All fade inspector layout checks passed** (23 checks), 2026-07-20.

Two script-side gotchas worth remembering (not app bugs): switching the
generator `<select>` write-through-persists new args onto the focused
message (use a per-kind fixture message instead), and per-element
`scrollIntoView` before `bounding_box()` makes rects incomparable —
gather all rects in one `page.evaluate`.

## Observed for ap-2

`inspector-narrow.png` shows the single-segment fade preview ending in a
sharp drop back to start. Suspect `shapeFraction("saw", fraction, …)` at
`fraction === 1` wrapping to 0 in the preview sampler (show.js ~line
589), so the last sample returns to the segment's start value.
