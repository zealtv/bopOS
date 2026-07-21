# Verification — plain step/divider glyphs (24/02)

## Change

`dashboard/static/js/show.js`: the three SVG-building constants from `19/02`
collapse to two characters.

```js
const ADD_STEP_GLYPH = "✛";     // U+271B open centre cross
const ADD_DIVIDER_GLYPH = "╱";  // U+2571 box drawings light diagonal
```

`dashboard/static/css/style.css`: `.show-edit-bar-glyph` width `20px` → `14px`
(back to a single-character slot) and the `.show-edit-bar-glyph svg` rule
dropped.

## Codepoints chosen, and why

The edit bar's existing vocabulary is `⧉` (U+29C9, duplicate) and `✕`
(U+2715, delete) — thin, uniform-stroke geometric symbols, noticeably lighter
than the ASCII `+` and larger than an ASCII `/` at the same font size.

- **`✛` U+271B, open centre cross** — reads as a plus, sits in ✕'s Dingbats
  family, and matches its stroke weight and optical size. ASCII `+` renders
  visibly smaller and thinner beside ✕ in the system UI font; `✚` (U+271A) is
  the heavy variant and shouts.
- **`╱` U+2571, box drawings light diagonal** — a full-cell diagonal with a
  uniform thin stroke, effectively one half of ✕, so the four glyphs read as
  one set. ASCII `/` is shorter and steeper and does not fill the slot.

Verified rendered, not just chosen on paper: see `edit-bar-1280-light.png`
(`✛ Step  ╱ Divider   ⧉ Duplicate  ✕ Delete` on one row — weights match) and
`edit-bar-768-dark.png` for the label-less state, plus the light/dark and
1280/768 `review-*` full pages.

## The `19/02` reasoning being overridden

`19/02` existed because at narrow widths the labels drop, and a bare `+` next
to a bare `—` read as add-step / remove-step. That defect does not return:
`╱` is not the visual opposite of `✛`, so the pair reads as two unrelated
"add …" actions rather than an opposed pair. Bob saw the drawn SVGs live and
judged them messy; a matched character set was the cheaper answer to the same
problem.

Held constant: accessible names `Add step` / `Add divider` (screen-reader
contract and Playwright selectors), the `aria-hidden` glyph span, and the
`⧉`/`✕` glyphs.

## Verifier

`verify_plain_glyphs.py` in this directory, derived from
`.loom/tied/02-step-and-divider-icons/verify_step_divider_icons.py` with the
drawn-SVG assertions replaced by character assertions.

```
$ ~/.venvs/bopos/bin/python .loom/threads/24-show-divider-and-glyph-repass/02-plain-step-divider-glyphs.stitching/verify_plain_glyphs.py
…
[PASS] 768px: add-step glyph is a single character, no svg
[PASS] 768px: add-divider glyph is a single character, no svg
[PASS] 768px: the two glyphs are distinct
[PASS] 768px: glyph slot back to a single-character 14px
[PASS] 768px: all four edit-bar buttons visible
[PASS] 768px: no edit-bar button overlaps a neighbour
[PASS] 768px: the edit bar itself does not overflow
[PASS] no page-level horizontal overflow at 768px
[PASS] browser emitted no page errors across all widths

0 failure(s)
```

Buttons still resolve by accessible name and still add the right item kind at
both widths (asserted earlier in the same run).

## Superseded tied assertions (repaired in place)

`.loom/tied/02-step-and-divider-icons/verify_step_divider_icons.py` asserted
that each glyph span contains a non-empty `svg`, that the two SVGs differ,
that their strokes resolve to `currentColor`, and that the glyph slot is
20px. All inverted to their character equivalents with an inline comment
naming this stitch, per the ruling in
`.loom/tied/03-divider-rule-styling/decisions.md`.
