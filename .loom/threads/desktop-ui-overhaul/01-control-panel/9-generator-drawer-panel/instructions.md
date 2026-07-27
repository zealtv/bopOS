# 9-generator-drawer-panel

Bring the generator drawer's **interior** into the ratified control-panel
language. Authority: the tied `2-control-panel-design` stitch —
`design-language.md` §7 (generator drawer), `control-panel-design.md` §3, and
`mockup-control-panel.html` panels 1 and 2 (the visual authority).

## Why this stitch exists

`4-row-regrind` reground the row and `3-tokens-and-chrome` restyled the drawer
*shell* (subpanel, indent, kind tabs). The drawer's **body** was left alone and
still renders `ParamGenerator.fields()` — the Show-inspector's stacked
`<label>text <input>` markup with a `.show-param-preview` figure below it. So
the drawer's layout and components do not match the mockup or the prototype:

- LFO fields are a two-column grid of labelled number inputs; the mockup is a
  waveform display with the shape select **inside** it, a side column of
  `phase` / `curve` mini-sliders with `free` below them, and an args row of
  `min` `max` `period` `[unit ▾]`.
- fade/loop segments are bordered stacked blocks with `destination` /
  `duration` / `Remove`; the mockup is one line per segment —
  `to [v] in [n] [unit ▾] (remove)` — under a curve display with a `from` box
  and a `curve` mini-slider beside it.
- The preview is a captioned figure below the fields rather than the display
  the layout is built around, and it has no playhead.

## Constraint

`ParamGenerator.fields()` is **shared with the Show inspector** and its markup
is deliberately common (see the module header). Do not regrind it in place —
the Show tab is not in this thread's scope and its density work is tied. Add a
panel-specific renderer alongside it, emitting the same `data-param-*` hooks so
`ParamGenerator.compile()`, the drawer binding, and the wire are untouched.

## Scope

- Panel-language LFO body, fade/loop body, and waveform display per §7.
- Playhead: only where the surface honestly knows the phase — the same
  `automationAnchors` elapsed value the row marker uses. No invented motion
  (the `8-kind-feedback-pass` ruling generalizes).
- CSS in `control-panel.css`, scoped to `.live-card` / `.device-control`.

Out of scope: the Show inspector, the wire grammar, `44`'s event drawer.

Verify: extend `tests/verify_generator_drawer.py` (the living journey that owns
this surface) — it currently pins `.show-param-preview` inside the drawer, and
that assertion is what changes. `tools/run-tests.sh browser` before tie.
