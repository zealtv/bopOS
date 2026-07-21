# 02-plain-step-divider-glyphs

**Bob, 2026-07-21:** "Let's remove the added iconography for step and
divider, it's messy. Make step just `+`, and divider `/`. Find icons for
those symbols that match the existing style."

`19/02-step-and-divider-icons` replaced both glyphs with inline SVG (a plus
followed by a rounded rect / a rule). Bob has seen it and rejected it. Revert
to single characters.

## Outcome

- Add step → a plus character. Add divider → a slash character.
- "Match the existing style" = the edit bar's existing plain-character glyph
  vocabulary, `⧉` (duplicate) and `✕` (delete). Choose the codepoints whose
  weight, size and optical alignment sit with those two rather than
  defaulting to the ASCII keyboard characters if a better-matched glyph
  exists — check it rendered, in both themes, at both widths, and record
  which codepoints were chosen and why.
- Remove the SVG entirely (both constants in `show.js`) and revert
  `.show-edit-bar-glyph` to the width a single character needs.
- Accessible names stay exactly `Add step` / `Add divider` — screen-reader
  contract and Playwright selectors.
- No icon font, no external asset.

## The reasoning being overridden

`19/02` existed because at narrow widths the labels drop and a bare `+`
beside a bare `—` read as add-step / remove-step. `/` is not the visual
opposite of `+`, so that specific confusion does not return. Record this in
the stitch — the defect was real, and the next person should see why it is
considered addressed rather than forgotten.

## Supersedes

`19/02`'s guard assertion that each glyph span contains an `svg`. Repair the
tied guard in place with a comment naming this stitch (see the thread
instructions).

## Verify

Playwright: both buttons still resolve by accessible name at wide and narrow
widths and still add the right item kind; the glyph spans contain the chosen
characters and no `svg`; no horizontal overflow at 768px. Screenshot the edit
bar at both widths, both themes. Re-run the tied Show guards.
