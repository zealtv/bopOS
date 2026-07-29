# 48-morph-interpolation

**Deferred by Bob, 2026-07-29.** This thread lives under `feature-backlog` for
later reconsideration. The move is a v1-scope ruling from
`41-preset-primitive/3-addendum-review` (F1), not a rejection of the design.

**FEATURE.** The `morph` wire grammar form: argument-vector interpolation into
a full-state generator spec, `morph <dur> [c:<n>] <destination-spec…>`,
evaluated by `bopos.py`. It lets a timed preset apply (or a hand-authored
message) glide a running LFO/loop's magnitudes into a destination generator
instead of snapping.

## Why it was deferred

Thread 41 ships timed preset application without it: **float/int entries fade
via the existing `x <dur> c:<n>` grammar; generator, toggle, enum, and text
entries set at t=0 and are counted in the apply report.** That covers the
workhorse case (morphing between scalar values) with zero contract change and
no engine work. Morph's whole payload is interpolating *generator arguments* —
the exotic case — at the cost of a new contract form, both parsers, engine
lerp machinery, simfleet parity, and catch-up serialization. Bob ruled the
simplicity trade the right call for v1. Nothing in the shipped design
forecloses morph: a preset entry is already the full-state argument list morph
would consume, so it lands purely additively.

## Design state — largely settled, do not redesign from scratch

The mechanism was designed, adversarially reviewed twice, and repaired. Read,
in order:

1. `.loom/tied/1-preset-architecture-design/proposal.md` §4 — the ratified
   argument-vector approach (F2: morph over the mix function).
2. `41-preset-primitive/design-addendum.md` §A1/§A2 — the repaired grammar
   (leading-option wrapper; the inner message goes verbatim to the existing
   parser) and the interpolation law (**magnitudes interpolate; anything
   defining time or shape takes the destination at t=0**, which keeps the
   generator clock-anchored and idempotent throughout, so catch-up sends the
   current interpolated spec). Bob's Q1 ruling: morph keeps its curve via the
   leading `c:` option.
3. `41-preset-primitive/3-addendum-review/review-2.md` F2/F4 — the review
   findings to fold in when reviving:
   - destination whitelist: must parse to `set`/`lfo`/`loop`; `stop`, bare
     fade forms, and nested `morph` are grammar errors;
   - phase lerps linearly (stated), catch-up serializes `p:` in range;
   - report/docs honesty: time and shape switch at onset even for "aligned"
     LFO↔LFO pairs — only depths glide;
   - kind-aware snapping (toggle/enum/text never sent as morph) lives in the
     preset application core, which will already exist.

## Shape when revived

Roughly the old §10.4 stitch: contract amendment (additive §3.2/§3.3 form),
`python/paramgen.py` + `dashboard/static/js/paramspec.js` parsers, engine lerp
slot in `bopos.py`, `tools/simfleet.py` parity, catch-up, take-over, int
quantization, browser-free guards — plus wiring the preset apply core's timed
path to emit `morph` for generator entries instead of snapping them.

Revive when fleet-wide generator sweeps (LFO depth/range glides between
presets) are actually missed in practice.
