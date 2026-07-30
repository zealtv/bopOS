# Decisions

## The card

`.show-rows-box` gains `background:var(--panel)` — §12's fix for the exact defect
Bob named. The inset `box-shadow` ring is **kept** rather than swapped for a real
`border`: it draws inside the box, on top of the row edges, so it stays a crisp
1px frame with no doubling against the collapsed row borders below, and it keeps
the `resize:vertical` grip and scroll edge behaving exactly as they did.

## It's a spreadsheet (Bob, 2026-07-30)

`.show-rows` `gap:3px` → `gap:0`, plus three consequences that had to be handled
or the result is worse than the gap was:

- **`.show-step-row` loses its radius and gains `margin-bottom:-1px`.** Each row
  keeps its own full border, and adjacent borders overlap into a single shared 1px
  gridline. Rounded corners on butted rows read as a stack of cards, not a sheet.
  Keeping all four edges (rather than switching to `border-bottom` only) matters
  because the row's state machinery tints `border-color` — focus, and the armed
  pulse animation — and those must still outline the whole row.
- **`.show-step-row.focused/.active/.show-step-armed` get `z-index:2`.** With
  collapsed borders the *next* row's plain border paints over the bottom edge of a
  tinted one, so a focused row would show three purple sides and one grey. The
  rows were already `position:relative`, so this is just a stacking fix.
- **`.show-step-progress` loses its radius** so the playback fill follows the
  row's new square corners instead of insetting at them.

`.show-divider-row` also loses its `margin:2px 0`. Its own 10px height is the
break; the margin would have reintroduced exactly the space Bob asked to remove,
in the two places most likely to look like a mistake.

## Row ink: left as-is, and why

Rows stay `--surface-bar` on a `--panel` card — slightly recessed cells on a
lighter sheet, which is the spreadsheet reading in both themes. The instructions
flagged that light-on-light might flatten; it does not (`#e9ecef` on `#f8f9fa`
with a `--line` gridline between).

**Finding, pre-existing, not fixed here:** in the light theme `--surface-bar` and
`--surface-alt` are **both `#e9ecef`**, so
`.show-divider-row + .show-step-row{background:var(--surface-alt)}` — the
"first row after a divider" distinction — is a **no-op in light**. Dark has it
(`#14191d` vs `#172027`). This arrived with the neutral-grey repaint in
`02-token-promotion`, not with this stitch, and whether that distinction is wanted
at all is a design question rather than a bug to quietly patch. Recorded for
`11-ground-and-card-audit`.

## Scope held

Only the Show list. The Control tab's §12 violations stay with `06` and `08`,
which own that surface, and the app-wide sweep is `11`. No JS, no markup.

---

## Follow-up rulings, same session (Bob, 2026-07-30)

### Dividers are the same height as steps, whatever they contain

Measured before changing anything: steps **34px**, unnamed dividers **18px**,
named dividers **26px** — three heights in a list that is meant to read as one
sheet.

34px was an *accident* (a `min-height:var(--row-h)` of 24px plus the 26px
transport button, padding and borders), so the fix declares it:
`--show-row-h:34px` on `.show-rows`. Steps take it as `min-height`, so a row
whose message pills wrap can still grow — that flexibility is deliberate and
worth keeping. Dividers take it as a fixed `height`, and `.show-divider-named`
drops `height:auto`/`min-height:26px`, which is what made a named divider taller
than an unnamed one.

### The first-step-after-divider tint is gone

`.show-divider-row + .show-step-row{background:var(--surface-alt)}` deleted. This
also retires the light-theme finding recorded above — the rule was a no-op there
because `--surface-alt` and `--surface-bar` are the same grey — so `11` no longer
inherits that question.

### Dividers select like steps

Bob: *"the purple selection is getting cut off when selecting dividers."*

Same root cause as the `z-index` fix earlier in this stitch, from the other
direction. Dividers used `outline:1px solid var(--accent)` with
`outline-offset:1px`, which paints **outside** the element. Once rows butt
together, each neighbour covers the offset ring, and the list box's scroll
clipping takes the rest — so the selection was cut off on every shared edge. It
was fine before only because the 3px gap left room for it.

Steps never had this problem because they ring with `box-shadow: inset`. Dividers
now join that rule (plus `z-index:2`), so one treatment serves both and neither
can be clipped. The divider's `border:0` makes the `border-color` half of that
rule inert, which is harmless — the inset shadow is what draws.

Verified at 34px with `boxShadow: … inset`, `outlineStyle: none`, `zIndex: 2` in
both themes, and photographed with a **named** divider selected — the case whose
ring was clipped worst — in `05g-final-list-{light,dark}.png`.

Both rulings are pinned in `tests/verify_show_reference_foundation.py`: equal row
heights, and the un-clippable ring asserted as *inset + no outline*, so a
well-meaning revert to `outline` fails the test rather than silently
reintroducing the clipping.
