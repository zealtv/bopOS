# Verification — divider rule styling (stitch 19/03)

Date: 2026-07-21. CSS-only change, `dashboard/static/css/style.css`.

## What changed

1. `.show-divider-row` (the appended block near line 57): dropped the
   `linear-gradient(...)` background (`background:none`) and lifted `opacity`
   from `.85` to `1` so the new flat rule reads as exactly `--strong-line`.
2. `.show-tab .show-divider-named .show-divider-line`: `flex:1 1 auto;
   min-width:8px` → `flex:0 0 28px` (fixed-length rules; `min-width` dropped as
   redundant under a fixed basis with no shrink).
3. New `.show-tab`-scoped block at the end of the named-divider section:
   - `.show-tab .show-divider-named{justify-content:center}`
   - `.show-tab .show-divider-named .show-divider-drag{position:absolute;
     left:8px;top:50%;transform:translateY(-50%)}`
   - `.show-tab .show-divider-row:not(.show-divider-named)::after{content:"";
     position:absolute;left:36px;right:8px;top:50%;height:1px;
     transform:translateY(-50%);background:var(--strong-line);
     pointer-events:none}`
   - `.show-tab .show-divider-named` padding `5px 8px` → `5px 34px`.

No JS, no HTML, no new colour tokens (`--strong-line` already resolves per
theme).

## Deviations from `decisions.md` (and why)

`decisions.md` says the named row "centres its contents (`justify-content:
center`, which `.show-divider-row` already sets — the named variant must not
re-override it)". That is true of the base `.show-divider-row` rule (line 61),
but the **compact-chrome block (stitch 18/05, line 56) already re-overrides it**
for the whole Show tab:

```
.show-tab .show-divider-row{box-sizing:border-box;justify-content:flex-start;padding-left:8px}
```

With the old `flex:1 1 auto` rules that override was invisible (the rules ate
all slack either way). With fixed 28px rules it is not: the group would sit
hard against the left edge. So the named variant must restore
`justify-content:center` — the ruled *intent* (centred name) requires
re-overriding the `.show-tab` override, not the base rule.

Second consequence: `justify-content:center` centres *all* flex children,
including the leading drag handle, which would push the name ~14px right of the
row's centre line. To put the name on the row's true centre (the verifier
asserts ≤4px), the named row takes the handle out of the flex flow
(`position:absolute` inside the already-`position:relative` row) and reserves
symmetric `34px` side padding (8px offset + 20px handle + 6px breathing room) so
the handle never collides with the left rule at narrow widths. Drag still works
— the drag logic keys off the button's `data-drag-item` and its bounding rect,
both unchanged.

`28px` is the ruled proposal and is retunable in exactly one declaration
(`.show-tab .show-divider-named .show-divider-line{flex:0 0 28px}`); the
unnamed rule's handle clearance is likewise one value (`left:36px`).

## Commands run and real output

### New verifier

```
cd /Users/bob/repos/bopOS
~/.venvs/bopos/bin/python .loom/threads/19-show-chrome-fixes/03-divider-rule-styling.stitching/verify_divider_rules.py
```

```
[PASS] named divider (short name) renders two rules and a name
[PASS] named divider (short name) rules are exactly 28px wide
[PASS] named divider (short name) rules are far narrower than the row
[PASS] named divider (short name) name is horizontally centred
[PASS] named divider (short name) rules flank the name
[PASS] named divider (short name) rules stay adjacent to the name
[PASS] named divider (short name) has no gradient background
[PASS] named divider (short name) keeps its row aria-label
[PASS] named divider (short name) keeps its drag-handle aria-label
[PASS] named divider (long name) renders two rules and a name
[PASS] named divider (long name) rules are exactly 28px wide
[PASS] named divider (long name) rules are far narrower than the row
[PASS] named divider (long name) name is horizontally centred
[PASS] named divider (long name) rules flank the name
[PASS] named divider (long name) rules stay adjacent to the name
[PASS] long divider name truncates instead of stretching the rules
[PASS] long divider name keeps the full text in the DOM
[PASS] named divider (long name) has no gradient background
[PASS] named divider (long name) keeps its row aria-label
[PASS] named divider (long name) keeps its drag-handle aria-label
[PASS] unnamed divider row exists with no rule/name spans
[PASS] unnamed divider has no background-image (gradient dropped)
[PASS] unnamed divider draws an ::after rule
[PASS] unnamed divider ::after rule is 1px high
[PASS] unnamed divider ::after rule is pointer-transparent
[PASS] unnamed divider still has a grab handle
[PASS] unnamed divider rule does not overlap the grab handle
[PASS] unnamed divider rule spans most of the row width
[PASS] unnamed divider keeps its row aria-label
[PASS] unnamed divider keeps its drag-handle aria-label
[PASS] focused divider row keeps a visible outline
[PASS] committed divider name shows on the row
[PASS] renamed divider keeps 28px rules
[PASS] renamed divider row aria-label follows the new name
[PASS] no page-level horizontal overflow at 1280px
[PASS] browser emitted no page errors

0 failure(s)
```

### Tied regression suites (run unmodified)

Each run below; only the `[FAIL]` lines and the trailing count are reproduced.

```
=== .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
0 failure(s)
=== .loom/tied/04-named-section-dividers/verify_named_dividers.py
[FAIL] unnamed divider row keeps the plain gradient rule (no name/lines) -- {'lines': 0, 'name': None, 'named': False, 'hasGradient': False, 'kids': ['show-drag-handle show-divider-drag']}
1 failure(s)
=== .loom/tied/05-compact-chrome/verify_compact_chrome.py
0 failure(s)
=== .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
0 failure(s)
=== .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
0 failure(s)
=== .loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
0 failure(s)
=== .loom/tied/02-step-and-divider-icons/verify_step_divider_icons.py
0 failure(s)
```

Afterwards: `git checkout -- .loom/tied/` (restored the tied screenshots) and
`find .loom/threads .loom/tied -name __pycache__ -type d -exec rm -rf {} +`.

## The one tied-suite conflict — STOPPED per spec, not edited

`.loom/tied/04-named-section-dividers/verify_named_dividers.py`, lines 268–271:

```python
unnamed = named_row_shape("d0000001")
check("unnamed divider row keeps the plain gradient rule (no name/lines)",
      unnamed["lines"] == 0 and unnamed["name"] is None
      and not unnamed["named"] and unnamed["hasGradient"], repr(unnamed))
```

where `hasGradient` is `getComputedStyle(row).backgroundImage.includes('gradient')`
(line 260, 265).

This assertion pins the exact thing Bob asked to be removed ("get rid of that
gradient… It can just be a blank line") and `decisions.md` rules away ("no
gradient and no background on the row"). It cannot be satisfied simultaneously
with this stitch's requirement 3 (`background-image` is `none`) unless the flat
rule were itself painted as a `linear-gradient` background, which
`decisions.md` explicitly forbids ("no gradient and no background on the row;
instead … an absolutely positioned `::after`").

Per the spec I did **not** edit the tied suite. The rest of the 04 suite
(named-row shape, line/name/line ordering, no gradient on named rows,
click-to-edit naming, drag, multi-client sync, narrow-viewport tap) passes
unchanged — this is the single failing check in that file. The orchestrator
needs to rule on how the superseded assertion is retired.

## Artifacts

- `dividers-1280-light.png`, `dividers-1280-dark.png` — full Show tab, both
  themes, containing an unnamed divider, a short-named divider (after the
  in-test rename to `RENAMED SECTION`), and a long-named truncating divider.
- `divider-rows-light.png`, `divider-rows-dark.png` — the rows box cropped, so
  the rule styling is legible at 1:1.
