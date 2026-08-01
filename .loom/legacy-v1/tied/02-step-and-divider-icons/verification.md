# Verification — step/divider glyphs (stitch 02)

## What changed

`dashboard/static/js/show.js` — two module-level glyph constants above
`editBarButton()`, built from one shared opening fragment so the plus is
literally identical in both icons:

```
viewBox="0 0 20 14" width="20" height="14" fill="none" stroke="currentColor"
stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
  plus:    M1 7 H7  and  M4 4 V10        (cross centred (4,7), arms ±3)
  step:    <rect x=10 y=3 width=9 height=8 rx=2 stroke-width="1.6"/>
  divider: M10 7 H19
```

The `add-step` / `add-divider` `editBarButton()` calls now pass those constants
instead of `"+"` / `"—"`. `escapeHtml` still wraps the labels and accessible
names; the glyph is still injected raw (it always was). `Duplicate` (`⧉`) and
`Delete` (`✕`) untouched.

`dashboard/static/css/style.css` — `.show-edit-bar-glyph` width `14px → 20px`,
plus one new rule `.show-edit-bar-glyph svg{display:block;flex:none}`. Nothing
else: button size, padding, `::after` touch expansion, and the
`@media(max-width:900px)` `.show-edit-bar-label{display:none}` behaviour are
unchanged.

## Deviations / implementer calls

- **`stroke-width="1.6"` on the step rect**, the option decisions.md left to the
  implementer. At 14px tall a 2px stroke on a 9×8 rect closed the interior up
  and read as a filled blob; 1.6 keeps it legibly a *box*. The plus stays at 2
  so the two icons' plus strokes match weight exactly.
- **No glyph-gap trim was needed.** The spec asked to check the widened glyph
  does not push the edit bar into overflow at 768px. It does not: the verifier
  asserts both `bar.scrollWidth <= bar.clientWidth` and no page-level horizontal
  overflow at 768px, and both pass. The 6px `gap` is unchanged.
- No other deviation from spec or decisions.

## Visual check

Retained, both themes, both widths: `edit-bar-{1280,768}-{light,dark}.png`
(cropped edit bar) and `review-{1280,768}-{light,dark}.png` (full page).
At 768px, with labels dropped, the pair reads `+▭` `+—` — one "add …" family,
no opposed add/remove pair. Disabled state is unaffected (the buttons are not
disabled; the sibling Duplicate/Delete `opacity:.4` treatment is untouched, and
the SVGs inherit `currentColor` so they would dim identically). The verifier
asserts each SVG's computed `stroke` equals its button's computed `color`,
which is what makes both the theme and the disabled case work.

## Commands run and real output tails

```sh
cd /Users/bob/repos/bopOS
~/.venvs/bopos/bin/python .loom/threads/19-show-chrome-fixes/02-step-and-divider-icons.stitching/verify_step_divider_icons.py
```

```
[PASS] 1280px: button resolves by accessible name 'Add step'
[PASS] 1280px: button resolves by accessible name 'Add divider'
[PASS] 1280px: add-step glyph span contains an svg
[PASS] 1280px: add-divider glyph span contains an svg
[PASS] 1280px: add-step svg is non-empty (>=2 shapes)
[PASS] 1280px: add-divider svg is non-empty (>=2 shapes)
[PASS] 1280px: the two svgs are distinct
[PASS] 1280px: glyph spans stay aria-hidden
[PASS] 1280px: svg strokes resolve to the button's currentColor
[PASS] 1280px: glyph slot widened to 20px
[PASS] fixture starts as 4 step rows, no dividers
[PASS] Add step appended exactly one row
[PASS] Add step added a STEP row (no divider appeared)
[PASS] Add divider appended exactly one row
[PASS] Add divider added a DIVIDER row (step count unchanged)
[PASS] 1280px: all four edit-bar buttons visible
[PASS] no page-level horizontal overflow at 1280px
[PASS] 768px: edit-bar labels are hidden (the reported condition)
[PASS] 768px: button resolves by accessible name 'Add step'
[PASS] 768px: button resolves by accessible name 'Add divider'
[PASS] 768px: add-step glyph span contains an svg
[PASS] 768px: add-divider glyph span contains an svg
[PASS] 768px: add-step svg is non-empty (>=2 shapes)
[PASS] 768px: add-divider svg is non-empty (>=2 shapes)
[PASS] 768px: the two svgs are distinct
[PASS] 768px: glyph spans stay aria-hidden
[PASS] 768px: svg strokes resolve to the button's currentColor
[PASS] 768px: glyph slot widened to 20px
[PASS] 768px: all four edit-bar buttons visible
[PASS] 768px: no edit-bar button overlaps a neighbour
[PASS] 768px: the edit bar itself does not overflow
[PASS] no page-level horizontal overflow at 768px
[PASS] browser emitted no page errors across all widths

0 failure(s)
```

Then the six tied suites, run **unmodified**:

```sh
~/.venvs/bopos/bin/python .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
~/.venvs/bopos/bin/python .loom/tied/04-named-section-dividers/verify_named_dividers.py
~/.venvs/bopos/bin/python .loom/tied/05-compact-chrome/verify_compact_chrome.py
~/.venvs/bopos/bin/python .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
~/.venvs/bopos/bin/python .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
~/.venvs/bopos/bin/python .loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
```

```
=== .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
[PASS] 768px stacks the inspector below the step list (single column)
[PASS] 768px toggle still collapses the sidebar
[PASS] no page-level horizontal overflow at 768px
[PASS] browser emitted no page errors across all widths

0 failure(s)
=== .loom/tied/04-named-section-dividers/verify_named_dividers.py
[PASS] a long divider name truncates/ellipsizes (scrollWidth > clientWidth)
[PASS] no page-level horizontal overflow at 768px with a long divider name
[PASS] touch tap on a divider title commits a rename
[PASS] browser emitted no page errors across all widths

0 failure(s)
=== .loom/tied/05-compact-chrome/verify_compact_chrome.py
[PASS] no page-level horizontal overflow at 768px
[PASS] inspector input keeps a >=44px min-height at <=760px
[PASS] no page-level horizontal overflow at 500px
[PASS] browser emitted no page errors across all widths

0 failure(s)
=== .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
[PASS] narrow client emitted no console/page errors
[PASS] empty show: Duplicate/Delete disabled (nothing to select)
[PASS] empty show: + Step appends the first row
[PASS] browser (wide) emitted no page errors

0 failure(s)
=== .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
[PASS] stacked panels each span the full container width at 768px
[PASS] both stacked panels share the same fixed expanded height at 768px
[PASS] no page-level horizontal overflow at 768px
[PASS] browser emitted no page errors across all widths

0 failure(s)
=== .loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
[PASS] 1280px tall inspector (LFO message): toggle hit area does not intersect delete button
[PASS] 1280px: toggle stays pinned to the panel's top-right
[PASS] 1280px: inspector heading keeps its 34px toggle reservation
[PASS] browser (wide) emitted no page errors

0 failure(s)
```

No tied suite matched on the literal `+` / `—` glyph text — the edit-bar suite's
"`+ Step` appends the first row" check resolves the button by accessible name,
not glyph, so it was unaffected.

Afterwards: `git checkout -- .loom/tied/` restored the tied suites' regenerated
screenshots, and `__pycache__/` directories under `.loom/` were removed. Nothing
was committed; the tree is left dirty for review.
