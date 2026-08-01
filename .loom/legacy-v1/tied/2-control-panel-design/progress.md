# Progress

2026-07-27 — First deliverable: `mockup-control-panel.html`, a live
self-contained prototype reproducing all three panels of Bob's Excalidraw
mockup (All Seats panel with open LFO drawer, fade drawer, non-float kinds)
plus a state legend for the row grammar. Reviewed live with Bob in-session.

Key synthesis: the dashboard token layer is already bop-PD-congruent —
`--accent` ≈ the bop panel periwinkle, `--accent-cyan` ≈ the PD number-box
cyan — and the mockup's name-inside-slider row is PD's `label: value` slider
idiom. The prototype uses the shipping token names/values (dark + light) so
it extends the design system rather than forking it. Cyan is reserved for
modulation/selection per the mockup; the base stays grayscale.

Row grammar as prototyped: `[value box][name-in-slider][∿ icon]` at 24px;
gray fill = manual value, cyan fill + marker line = generator-driven
(precise position visible), gray cross-hatch = mixed values, cyan
cross-hatch = mixed with a generator involved; drawer is an inline subpanel
with a pointer up to its row's ∿ icon.

Live-review rulings from Bob (2026-07-27, second pass):
- Sub-element labels sit to the LEFT of their control; parameter rows put
  the name INSIDE the control. Mini-sliders (phase/curve) also carry their
  label inside, PD-style.
- Every slider gets a marker line at the current value — gray ink manual,
  cyan ink generator-driven.
- Mixed and mixed+generator are the SAME slash pattern, different ink
  (gray vs cyan); no crosshatch. The value box hatches too; dots go cyan
  when a generator is involved.
- `free` lives below `curve` in the drawer's side column — grouped with
  time by sitting above the duration unit. min/max/period boxes keep full
  padding (precision entry matters more than one-line compactness).
- Palette ruling: pink/purple + cyan ARE the foundational palette. Light
  theme's foundational BG is a saturated pink pastel (#f4d7eb); cyan is
  electric (#4DEEE3 dark / #0798BC light); focus rings and accent-color
  are the purple accent — no off-book colors (the browser-default orange
  focus ring was explicitly called off-book).

Third pass (same session): electric cyan (#4DEEE3/#0798BC), saturated pink
light base (#f4d7eb), free below curve, full-width arg boxes, on-book purple
focus ring (accent-color + :focus-visible), event boxes widened, and the
momentary/toggle distinction — momentary = rounded (PD bang), latching =
sharp (PD toggle box), keyed off `button[aria-pressed]`; ∿ icon stays a
circle as its own element class.

Docs drafted for ratification:
- `design-language.md` — tokens, row grammar, ink rules, button shapes,
  interaction/motion rules (the `02-app-wide-rollout-design` input).
- `control-panel-design.md` — panel anatomy, kind table (events flagged as
  the 44 contract question), mapping onto the shipping `ControlSurface`
  (evolve, don't fork; keep the native range input), five-child
  implementation split, verification plan, open questions Q1–Q4.

RATIFIED 2026-07-27 (live session). Bob's rulings: Q1 cyan only under
generators; Q2 enums automate like ints; Q3 light cyan stays #0798BC;
Q4 takeover status line stays. Final refinements before lock-in: integer
number boxes right-align (floats left-align — alignment says the kind),
momentary radius softened 10px → 7px, and the segment `in` boxes joined the
standardized 58px number-box width.

Implementation children laid out as siblings 3–7 under `01-control-panel`:
3-tokens-and-chrome, 4-row-regrind, 5-hierarchy-and-persistence,
6-non-float-kinds, 7-preset-slot. This design stitch is tied; its
`design-language.md`, `control-panel-design.md`, and `mockup-control-panel.html` are the
authority those children (and `02-app-wide-rollout-design`) build against.
