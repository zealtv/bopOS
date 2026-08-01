# 25-message-pill-encoding

**Complete, 2026-07-23.** The ratified eight-category palette, visible codes,
theme tokens, accessibility treatment, and focused browser verification are
tied.

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

## One flat collection (Bob, 2026-07-23 — resolves the design question)

Bob collapsed the two-dimension framing: **the colours are a single flat set of
categories combining payload mode *and* generator**, not two dimensions to
compose. His enumeration:

> cue, point, raw, param-value, param-fade, param-lfo, param-stop

So each of those is one colour in one palette — `point` gets its own colour
(distinct from `cue`), the non-param modes (`cue`, `point`, `raw`) are flat
categories, and the param modes are split by generator into `param-<generator>`.
This removes the "how to encode two dimensions on a 22px pill" problem entirely:
it's a **7-way categorical colour scheme**, one swatch per category.

**Confirm in the design:** Bob's list has seven and omits `loop` (the
`#show-param-generator` select, `show.js:648`, offers `value, fade, loop, lfo,
stop`). Settle whether `loop` folds into another category, is deliberately
excluded, or was an oversight and there should be a `param-loop` (eight total).

## The design question (now: the palette)

The remaining work is a **categorical palette** for those 7 (or 8) categories
that reads in light and dark, distinguishes neighbours, and doesn't collide with
the pill's existing state paint — `border-color` on focus and `box-shadow` on
drag/drop (`.show-drop-before` / `.show-drop-after`). A leading swatch, a fill,
or a glyph are all live; a stroke-heavy encoding may fight the focus/drop states.
Consult a UI/dataviz expert on the categorical palette (Bob asked for a design
expert, and this is now squarely a categorical-colour problem — the `dataviz`
skill's palette guidance applies).

## Shape of the work

1. `01-pill-encoding-design` — **ratified by Bob 2026-07-23**: eight flat
   categories including loop, tinted fills plus visible kind codes.
2. `02-pill-encoding-implementation` — build the ratified design.

The user-facing design gate is satisfied. The tied decision record is the
implementation authority.
