# 01-pill-encoding-design

Bob asked for this one to go to a UI/UX design expert to ideate. Produce a
proposal with real alternatives, recommend one, surface it to Bob, mark this
stitch `.waiting`, and tie it with the ratified design as `decisions.md`.

Read the parent `instructions.md` first — it states the problem and the current
hash-based palette.

## The problem — revised by Bob, 2026-07-23

The parent's newer ruling supersedes the original two-dimensional brief.
Design one flat categorical set: `cue`, `point`, `raw`, `param-value`,
`param-fade`, `param-lfo`, and `param-stop`, plus a ruling on the omitted
`param-loop`. There is no independent mode/generator visual composition.

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

- At least three sketched categorical-palette treatments. Each must cover
  failure modes at density, in both themes, under CVD, and when the pill is
  focused or dragging.
- A recommendation with reasoning.
- Whether the omitted `loop` gets its own category, folds into another
  category, or is deliberately excluded.
- Concrete token names and values, ready for the implementation stitch.
- ASCII/SVG sketches in markdown so Bob can read it without running anything.
- Keep the full proposal as a lore item if it is substantial; `decisions.md`
  lands in this stitch only once Bob ratifies.

Do **not** touch `show.js` or `style.css`.
