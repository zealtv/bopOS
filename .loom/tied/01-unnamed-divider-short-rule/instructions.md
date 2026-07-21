# 01-unnamed-divider-short-rule

**Bob, 2026-07-21:** "I'd like the dividers with no aliases to only have a
short rule, centered where their alias would go."

`19/03-divider-rule-styling` shipped the unnamed divider as a flat 1px rule
spanning the row (an absolutely positioned `::after`, inset left of the grab
handle to the right edge). Bob wants it short and centred instead.

## Outcome

- Unnamed divider: one short rule, horizontally centred in the row, sitting
  where a named divider's name sits. No gradient (that ruling stands).
- The two divider states should read as one row type: named = short rule,
  name, short rule; unnamed = short rule where the name would be. Pick the
  length so the unnamed rule looks deliberate next to the named row's two
  28px flanking rules — state the value and the reasoning.
- Grab handle retained and untouched; the rule must not run under it.
- Row stays focusable with its existing `aria-label`, drag behaviour, focus
  outline, and drop indicators.
- CSS only. Light and dark both checked.

## Supersedes

The `::after` full-width rule from `19/03`, and that stitch's guard assertion
about its geometry. Repair the tied guard in place with a comment naming this
stitch (see the thread instructions).

## Verify

Playwright per `CLAUDE.md` ("Dashboard browser tests"): assert the unnamed
rule's width is bounded (far less than the row width), that it is centred in
the row within a small tolerance, and that it does not overlap the grab
handle — all rects from a single `page.evaluate`. Screenshot both divider
states in both themes. Re-run the tied Show guards.
