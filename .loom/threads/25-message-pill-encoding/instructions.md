# 25-message-pill-encoding

Make the Show tab's message pill colours *mean* something.

**Bob, 2026-07-21:** "In the show tab message pills, colours reflect the payload
mode (parameter, cue point, raw) and generator — value, fade, loop, lfo, stop.
Design question: how to represent two dimensions. Mix of fill colour and stroke
style? Something else? Stitch should include asking a UI design expert."

## Where it stands today

`pillColourClass()` in `dashboard/static/js/show.js:130` hashes the message and
takes `hash % PILL_PALETTE_SIZE`, yielding one of eight `.show-pill-0..7`
classes defined in `dashboard/static/css/style.css` (dark) and repeated under
`:root[data-theme=light]`. The colour is therefore **arbitrary but stable** —
it distinguishes one pill from its neighbours and carries no semantics at all.

Bob wants that slot spent on meaning instead.

## The two dimensions

- **Payload mode** — `param`, `cue`, `point`, `raw`. Note Bob named three
  ("parameter, cue point, raw"); the code has four, and `point` is a distinct
  mode from `cue` (`show.js:599` disables targeting for both). Settle whether
  `point` gets its own encoding or Bob was collapsing the two.
- **Generator** — `value`, `fade`, `loop`, `lfo`, `stop` (the
  `#show-param-generator` select, `show.js:648`). This dimension **only exists
  for numeric `param` messages** — `rawFallback` and the non-param modes have no
  generator. So the two dimensions are not orthogonal: the second is conditional
  on the first. That asymmetry is a gift to the design, not an obstacle.

## The design question

How do you encode two dimensions on a 22px-tall pill that also carries text, a
drag affordance, a focus ring, and drop-target shadows? Fill vs stroke style is
Bob's opening suggestion; a glyph, a leading swatch, a stroke weight, or a shape
change are all live. Constraints that will bite: the pill already spends
`border-color` on focus and `box-shadow` on drag/drop (`.show-drop-before` /
`.show-drop-after`), so a stroke-heavy encoding may collide with existing state.

## Shape of the work

1. `01-pill-encoding-design` — UX proposal, **Bob ratifies before implementation**.
2. `02-pill-encoding-implementation` — build the ratified design.

House rule: user-facing dashboard design is a Bob gate. Do not implement past an
unratified design.
