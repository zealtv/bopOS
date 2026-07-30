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
