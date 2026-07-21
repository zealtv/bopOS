# 01-pill-encoding-design

Bob asked for this one to go to a UI/UX design expert to ideate. Produce a
proposal with real alternatives, recommend one, surface it to Bob, mark this
stitch `.waiting`, and tie it with the ratified design as `decisions.md`.

Read the parent `instructions.md` first — it states the problem and the current
hash-based palette.

## The problem

Encode **two** dimensions on one small pill:

- payload mode — `param` / `cue` / `point` / `raw`
- generator — `value` / `fade` / `loop` / `lfo` / `stop`, present **only** on
  numeric `param` messages

...where the second is conditional on the first, so the encoding must degrade
gracefully to "mode only" for three of the four modes.

## Requirements

- **Legible at a glance in a dense row.** The whole point of the Show tab is
  Ableton-density scanning; if you have to squint to tell `fade` from `lfo`, the
  encoding has failed. State the intended reading distance/effort.
- **Both themes.** Light is now purple-and-cyan after `21-theme-cyan-tint`
  (tied) — read `.loom/tied/21-theme-cyan-tint/` for the token layer, the
  semantic invariant on `--green`, and the contrast ratios before proposing
  colours. That stitch explicitly left the `.show-pill-*` categorical set
  untouched and flagged that pill-0 (176°) would collide with pill-7 (187°)
  under the new accent — your design is the thing that resolves that.
- **Do not collide with existing pill state.** `.show-message-pill.focused`
  spends `border-color` + inset `box-shadow`; `.show-drop-before/after` spend
  `box-shadow`; `.show-pill-drag` occupies the leading edge. Say explicitly how
  your encoding coexists with focus, drag, and drop-target rendering.
- **Accessibility.** Colour alone must not be the only channel — that is half of
  why Bob is asking about stroke style. Aim for a redundant encoding, and check
  it survives the common colour-vision deficiencies.
- **Token layer, not call sites** — same house rule the theme repass followed.
  Semantic colours (`--green` = success/online) stay distinguishable.
- **Losing the hash.** The current palette gives adjacent pills distinct colours.
  A semantic encoding means two `param`/`value` pills now look identical. Decide
  whether that is fine (probably: the *text* distinguishes them) or whether some
  residual per-message differentiation is worth keeping.

## Deliver

- At least three sketched alternatives — e.g. fill=mode + stroke-style=generator;
  fill=generator + a leading mode swatch/glyph; a monochrome pill with a glyph
  pair; shape/radius as one of the channels. Each with its failure modes at
  density, in both themes, under CVD, and when the pill is focused or dragging.
- A recommendation with reasoning.
- Whether `point` is its own encoding or folds into `cue` (Bob named three modes,
  the code has four) — this is a question for Bob if you cannot settle it.
- Concrete token names and values, ready for the implementation stitch.
- ASCII/SVG sketches in markdown so Bob can read it without running anything.
- Keep the full proposal as a lore item if it is substantial; `decisions.md`
  lands in this stitch only once Bob ratifies.

Do **not** touch `show.js` or `style.css`.
