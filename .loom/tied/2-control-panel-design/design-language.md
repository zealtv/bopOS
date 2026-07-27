# bopOS desktop design language — v1 draft (2026-07-27)

The extrapolable rulebook behind the control-panel design. This file is the
input `02-app-wide-rollout-design` consumes; the control panel
(`control-panel-design.md`) is its reference implementation. The living
prototype is `mockup-control-panel.html` — where prose and prototype
disagree, the prototype as last reviewed by Bob wins, then fix the prose.

Heritage: Pure Data (bop's own patches), Ableton, MaxMSP. The language is
tight, compact, monospace, grayscale-plus-two-hues. Congruence with bop in
PD is a design goal, not a nicety: the same person patches in PD and
operates bopOS.

## 1. Palette

**Pink/purple and cyan are the foundational palette.** No other hues may
appear in chrome or controls. (Status colors — the existing
green/amber/red tokens — remain legal for status *semantics* only: online
dots, warnings, errors. Never for controls or selection.)

Cyan means **modulation** first, selection second. Purple is the structural
accent (focus, selection chrome, brand). If a new highlight is ever needed,
it is a purple of similar saturation — never a new hue (Bob, 2026-07-27,
ruling out the browser-default orange focus ring).

Token values (dark / light):

| token          | dark                  | light                 | role |
|----------------|-----------------------|-----------------------|------|
| `--bg`         | `#101316`             | `#f4d7eb`             | app background; light mode is deliberately a saturated pink pastel |
| `--panel`      | `#191e23`             | `#fdf6fb`             | panel body |
| `--subpanel`   | `#12191e`             | `#f6e4f0`             | drawers, nested regions |
| `--input`      | `#10161b`             | `#fefcfe`             | value boxes, slider troughs |
| `--control`    | `#273039`             | `#eed7e8`             | button faces |
| `--hover`      | `#252d34`             | `#e5c6dd`             | hover on button faces |
| `--line`       | `#5e6a75`             | `#9a8298`             | structural rules |
| `--control-line` | `#74818c`           | `#84788a`             | control borders, manual marker ink |
| `--group-line` | `#3e4952`             | `#a586a0`             | panel/drawer borders |
| `--text`       | `#e8edf1`             | `#2b2130`             | primary text |
| `--dim`        | `#8f9ba5`             | `#655a6b`             | labels, secondary text |
| `--accent`     | `#8A82D8`             | `#7A4FC8`             | purple: focus, selection chrome |
| `--mod`        | `#4DEEE3`             | `#0798BC`             | electric cyan: modulation ink (borders, text, markers, playheads) |
| `--mod-fill`   | `rgba(77,238,227,.26)`| `rgba(7,152,188,.20)` | cyan area fill (slider fill, active toggle face) |
| `--mod-hatch`  | `rgba(77,238,227,.45)`| `rgba(7,152,188,.42)` | cyan hatch ink (mixed + generator) |
| `--mod-soft`   | `rgba(77,238,227,.12)`| `rgba(7,152,188,.09)` | faint cyan face (active tab, ∿ icon face) |
| `--value-fill` | `rgba(255,255,255,.10)` | `rgba(90,60,120,.13)` | gray/purple-gray manual-value fill |
| `--hatch`      | `rgba(255,255,255,.16)` | `rgba(60,40,80,.20)`  | gray hatch ink (mixed values) |

Light-mode cyan is capped by legibility: `--mod` doubles as text/border ink
on near-white, so it cannot go as electric as dark. If a hotter light cyan
is wanted later, split the token into fill-ink and text-ink; do not brighten
`--mod` past contrast.

Rollout note: these extend the shipping token layer in
`dashboard/static/css/style.css`. `--mod*` and `--value-fill`/`--hatch` are
new; the light-theme base tokens *change value* toward the pink pastel —
that repaint is an explicit, Bob-visible step in the rollout, not a silent
side effect of the control panel.

## 2. Focus and system colors

The app defines its own focus treatment; **no user-agent colors leak
through**. Concretely:

```css
:root { accent-color: var(--accent); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
```

Any native widget that still paints its own chrome (selects, checkboxes,
scrollbars where styled) inherits `accent-color`.

## 3. Type and numerals

- Monospace everywhere: `ui-monospace, SFMono-Regular, Menlo, Consolas,
  monospace`. Base size 12px, line-height 1.35.
- Numeric displays use `font-variant-numeric: tabular-nums`.
- Panel titles 14px bold; sub-labels 11–12px in `--dim`. No uppercase
  transforms in the new language (existing uppercase labels are repainted
  during rollout, not imitated).

## 4. Metrics

| token | value | applies to |
|-------|-------|------------|
| `--row-h` | 24px | parameter rows, value boxes, toggles |
| `--gap` | 6px | vertical rhythm inside a panel; grid gap in rows |
| mini-slider height | 16px | drawer sub-sliders (phase/curve) |
| value-box width | 58px | **the standard number-box width** — every numeric entry box (param rows, drawer args, segment `to`/`in`, event values) unless a box must hold visibly longer values |
| `--radius-panel` | 6px | panels |
| `--radius-control` | 4px | selects, text inputs |
| `--radius-small` | 3px | value boxes, sliders |
| `--radius-momentary` | 7px | momentary buttons |
| `--radius-toggle` | 1px | latching buttons, tabs |
| ∿ icon | 18px circle | modulation icon |
| drawer indent | 12px left margin | generator drawers, accordion children |

One parameter per line. Rows are never taller than `--row-h`; anything that
needs more height is a drawer or a subpanel, not a taller row.

## 5. The parameter row grammar

```
[ value box 58px ][ name-in-slider (flexible) ][ ∿ 18px ]
```

- **Value box**: bordered `--input` box, tabular numerals, click-to-type
  precision entry (see §9). Shows the live value at display precision;
  typing accepts full precision. **Alignment says the kind: floats
  left-align, integers right-align** (Bob, 2026-07-27).
- **Slider**: `--input` trough, 1px `--control-line` border. The parameter
  **name lives inside the slider**, left-aligned — PD's `label: value`
  slider idiom. A fill bar shows the value; a 1.5px **marker line** sits at
  the exact current value on every slider, manual or modulated.
- **∿ icon**: 18px circle at row end. Idle: `--dim` on `--input`. Active
  (generator running or drawer open): `--mod` ink, `--mod` border,
  `--mod-soft` face. Click toggles the generator drawer (§7).

Label placement convention (Bob, 2026-07-27): **parameter rows put the name
inside the control; sub-element labels sit to the left of their control.**
Drawer args (`min`, `max`, `period`) label above-left in `--dim`; inline
sub-elements (`from`, `to … in …`) label left. Mini-sliders are controls,
so their label goes inside, like big sliders.

## 6. State encoding (the ink rules)

Two axes: value agreement (unified / mixed) and drive (manual / generator).
One pattern language, two inks:

| state | slider | value box | ∿ icon |
|-------|--------|-----------|--------|
| unified, manual | `--value-fill` fill to value + `--control-line` marker | value, `--text` | idle |
| unified, generator | `--mod-fill` fill *following the modulated value* + `--mod` marker | live value, `--mod` text | active |
| mixed, manual | full-width 45° slash hatch in `--hatch` | `·····` dots, hatched box | idle |
| mixed, generator involved | same slash hatch in `--mod-hatch` | cyan dots, cyan-hatched box | active |

Rules behind the table:

- **Mixed is one pattern, two inks** — 45° slashes (4px/1.5px rhythm).
  Never a different pattern (crosshatch is out); the ink alone says whether
  a generator is involved.
- **Generator state is always visible on the control itself.** Numeric:
  fill and marker animate with the modulated value. Toggle: the control
  flashes its live on/off value and wears a `--mod` border
  (double-outlined). Deterministic generators (LFO shapes, loop, fade —
  and sample+hold/drift where the runtime can know the value) also show the
  precise current value in the value box.
- **Editing unifies.** Any manual interaction with a mixed or
  generator-driven control sets all targeted members to the entered value
  and the control renders solid — the §3.2 hard-takeover semantics made
  visible.

## 7. Generator drawer

- Opens/closes from the row's ∿ icon; drawer is a `--subpanel` region,
  indented 12px, with a small pointer up to the icon. Closing the drawer
  does **not** stop the generator; stop is takeover (§6) or an explicit
  stop control.
- Kind tabs — `LFO | loop | fade` — are latching buttons (sharp radius),
  active tab in `--mod-soft`/`--mod`.
- LFO layout: waveform display (cyan trace, cyan playhead line, shape
  select bottom-right *inside* the display) with a side column of
  mini-sliders (`phase`, `curve`) and the `free` toggle **below `curve`,
  above the duration unit** — grouped with time by adjacency. Args row:
  `min` `max` `period` `[unit ▾]`.
- Fade layout: curve display; side column `from` box and `curve`
  mini-slider; segment rows `to [v] in [n] [unit ▾] (remove)`; momentary
  `add segment`.
- Arg boxes keep full 58px width — precision entry beats one-line
  compactness; the row may wrap before boxes shrink.

## 8. Buttons

PD heritage decides the shapes: **a bang is a circle, a toggle is a square
box.**

- **Momentary** (acts once): `--radius-momentary` (rounded, not a full
  pill — 7px). Face
  `--control`, hover `--hover`. Examples: send all, new/save/del, remove,
  add segment, send.
- **Latching** (holds state): `--radius-toggle` (near-square). Pressed
  state face `--mod-fill` with `--mod` border. Examples: free, sync,
  enable-fx, kind tabs. Markup carries `aria-pressed`; the CSS keys the
  sharp radius off `button[aria-pressed]`, so semantics and appearance
  cannot drift apart.
- **∿ icon** is its own element class (disclosure + state indicator),
  always an 18px circle — exempt from the momentary/toggle radii.

## 9. Interaction rules

- **Click-to-type everywhere**: every numeric display is precision entry
  (the shipping `PrecisionField` behavior). Full typed precision reaches
  the wire; the display may round.
- **Hard takeover**: manual interaction with a generator-driven control
  stops the generator for the touched members and sends the manual value
  (contract §3.2). No confirmation, announced via the row's status output.
- **Hierarchy accordions**: nested addresses render as `▸ name` /
  `▾ name` disclosure rows; children indent 12px. Collapsed state persists
  per address (localStorage) so an operator's pruning survives re-render.
- **Drawer editing survives the heartbeat**: open-drawer and draft state
  live outside the DOM (as `ControlSurface` already does with
  `openDrawers`/`drafts`).

## 10. Motion

- Fill and marker of a generator-driven slider move with the modulated
  value (CSS animation for periodic shapes, rAF for fades — the shipping
  mechanism). The drawer waveform shows a moving playhead.
- Generator-driven toggles flash at their actual value transitions, not a
  cosmetic blink rate.
- `prefers-reduced-motion`: continuous animation degrades to ≥1s stepped
  updates (the shipping fade behavior generalizes).

## 11. Status colors

Green/amber/red stay reserved for status semantics (connectivity, warnings,
errors) at their existing token values. They never appear on controls,
fills, or selection. This keeps the control surface strictly
pink/purple + cyan while diagnostics stay legible.
