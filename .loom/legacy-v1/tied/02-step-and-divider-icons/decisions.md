# Decisions — step/divider glyphs (stitch 02)

Orchestrator ruling, 2026-07-21. Bob's complaint: at narrow widths the edit
bar drops the labels, leaving `+` (add step) beside `—` (add divider), which
reads as an opposed add/remove pair.

## Ruled answer

**Both glyphs carry an explicit plus, followed by a shape naming what is
added.** The additive sense then survives label-less rendering, and the two
glyphs are no longer an opposed pair — they are two members of one "add …"
family.

- **Add step** → `+` followed by a small rounded rectangle (a step row).
- **Add divider** → `+` followed by a single horizontal rule.

## Why inline SVG rather than text characters

The app already uses inline SVG for a glyph (`.device-mute-indicator svg`,
`fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;
stroke-linejoin:round`) and the house rule forbids an icon font or any
external asset. Two-character text composites (`+▭`, `+—`) depend on font
coverage and metrics we do not control, and at 13px the box character is
unreliable across platforms. Inline SVG is self-contained, inherits
`currentColor` (so it works in both themes and in the disabled state), and
scales with the existing glyph slot.

## Geometry

One shared `viewBox="0 0 20 14"`, `width="20" height="14"`, `fill="none"`,
`stroke="currentColor"`, `stroke-width="2"`, round caps/joins, matching the
mute-indicator conventions.

- Plus (both icons): a cross centred at `(4,7)`, arms ±3 — i.e. lines
  `M1 7 H7` and `M4 4 V10`.
- Step shape: rounded rect `x=10 y=3 width=9 height=8 rx=2`
  (stroke-width may drop to 1.6 on the rect if 2 reads too heavy at 14px —
  implementer's call, note it).
- Divider shape: line `M10 7 H19`.

`.show-edit-bar-glyph` widens from `14px` to `20px` to hold them. The narrow
button is 40px wide with 6px padding (28px of content), so 20px fits.

## Held constant

- The accessible names stay exactly `Add step` / `Add divider`
  (`title` + `aria-label`) — screen-reader contract and Playwright selectors.
- The glyph span stays `aria-hidden="true"`.
- The `Duplicate` (`⧉`) and `Delete` (`✕`) glyphs are untouched — they are
  not part of the confusion and not part of an add family.
- Both buttons behave identically to before; this is presentation only.
