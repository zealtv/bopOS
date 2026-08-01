# 05g-show-list-card

Put the Show tab's step list on a card.

Bob, 2026-07-30, reviewing the shipped tabs: *"the show step list looks broken
because the steps aren't atop a neutral card."*

Ratified as **design-language §12** (ground and card) in the same review:
`--bg` is the workspace ground, visible only as gutter *between* cards. Nothing
but the page paints it, and a bordered region with a transparent background is
the specific mistake — it reads as an empty container with things floating in it.

## The cause

`.show-rows-box` in `style.css` sets `box-shadow:inset 0 0 0 1px var(--line)`
and `border-radius:var(--radius-control)` and **no background**. `.tab-panel` is
`background:transparent`, so the box and the 3px gaps between rows show `--bg`
straight through from `body`.

The rows themselves are fine (`.show-step-row` is `--surface-bar`,
`.show-divider-row + .show-step-row` is `--surface-alt`), which is why the defect
reads as "the steps aren't on a card" rather than "the theme is wrong."

**The diagnostic detail:** `.show-transport-strip` and `.show-inspector-panel`
both set `background:var(--panel)` and look correct. Only the list between them
was left unbacked. This is per-surface drift, not a theme bug — the same shape as
the component-ownership defects `05b`–`05e` chased.

## Work

- Give the step list a card: `--panel` background on the appropriate element,
  and consider whether the inset border is still the right edge treatment once it
  has a background (a card usually wants a real `border`, not an inset shadow, so
  the resize handle and scroll edge behave).
- Watch the scroll and resize affordances: `.show-rows-box` is
  `overflow-y:auto; resize:vertical` and `.show-rows-resize` sits below it. A
  background must not swallow the resize grip or clip the sticky inspector.
- Check the row inks still read against the card. `--surface-bar` rows on a
  `--panel` card is a lighter-on-light pairing in the light theme; if it flattens,
  the recessed surface for the list interior is `--deep`/`--subpanel` (§1), with
  rows staying `--surface-bar`. Say which you chose and why.
- **Both themes.** The light repaint is the one Bob is looking at, but dark must
  not regress.

## Verification

`tools/run-tests.sh browser` for regressions, and a screenshot pair of the Show
tab in **both** themes — this is a purely visual defect, so a computed-style diff
proves nothing a picture doesn't. The `shoot.py` harness is in
`.loom/tied/02-token-promotion/`; note the bug that stitch recorded, that it
writes `bopos.theme` while `theme.js` reads `bopos-theme`, or the dark shots come
out light.

Scoped deliberately to the Show list. The Control tab's §12 violations belong to
`06` and `08`, which already own that surface, and the app-wide sweep for other
instances is `11-ground-and-card-audit`.
