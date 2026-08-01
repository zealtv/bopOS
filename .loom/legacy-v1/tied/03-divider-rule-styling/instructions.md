# 03-divider-rule-styling

**Defect (Bob, 2026-07-21):** two changes to the divider row shipped by
`18-show-chrome-density/04-named-section-dividers`.

1. **Named dividers:** "the lines either side of the divider title [should] not
   extend the whole way across the divider... just two short lines either side
   of the divider title." Bob is referring to the `01-layout-review` prototype
   screenshot — look for it in `.loom/tied/01-layout-review/` (and in the
   `2026-07-20-show-chrome-density-braindump` lore item) before guessing.
2. **Unnamed dividers:** "get rid of that gradient. We don't need it anymore
   now that we have the grab handle. It can just be a blank line."

## Outcome

- Named divider: short fixed-length rules flanking the centred name, not
  `flex:1` full-bleed rules. The name stays centred and stays click-to-edit
  (the unified title pattern ruled by Bob 2026-07-21 — see the comment at the
  top of `show.js`).
- Unnamed divider: a plain single line, no gradient, grab handle retained.
- Both remain focusable rows with their existing `aria-label`s and drag
  behaviour.
- CSS only where possible: `.show-divider-line` / `.show-divider-named` /
  `.show-divider-row` in `dashboard/static/css/style.css`. Light and dark
  themes both checked.

## Verify

Screenshot both divider states in both themes; Playwright assertion that the
rule elements have a bounded width (not the row width) on a named divider.
