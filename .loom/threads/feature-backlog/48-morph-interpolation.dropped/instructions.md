# 48-morph-interpolation

**Status:** parked by Bob, 2026-07-29 (v1 scope cut from `41-preset-primitive`,
not a rejection)
**Goal:** the `morph` wire form — `morph <dur> [c:<n>] <destination-spec…>` —
so a timed preset apply can glide a running LFO/loop's settings instead of
snapping.

**Revive when** glides between generator presets (e.g. LFO depth sweeps) are
actually missed in practice.

## Why it waited

Presets shipped without it: float/int entries fade with the existing
`x <dur> c:<n>`; generator, toggle, enum and text entries set at t=0. That
covers the common case with no contract change. Morph only adds generator
*argument* interpolation, at the cost of a new contract form, two parsers,
engine lerp, simfleet parity and catch-up. Nothing shipped blocks adding it
later.

## Design is mostly done — don't start over

Read in order:

1. `.loom/legacy-v1/tied/1-preset-architecture-design/proposal.md` §4 — the
   ratified argument-vector approach.
2. `.loom/legacy-v1/tied/41-preset-primitive/design-addendum.md` §A1/§A2 — grammar (leading options
   wrapping an inner message passed verbatim to the existing parser) and the
   rule: **magnitudes interpolate; anything defining time or shape switches to
   the destination at t=0**. Morph keeps its curve via `c:` (Bob).
3. `.loom/legacy-v1/tied/3-addendum-review/review-2.md` F2/F4 — fold in:
   destination must parse to `set`/`lfo`/`loop` (not `stop`, bare fades or
   nested `morph`); phase lerps linearly and catch-up serialises `p:` in range;
   docs must say time/shape switch at onset even LFO→LFO; kind-aware snapping
   lives in the preset apply core.

## Work when revived

Additive contract amendment (§3.2/§3.3); parsers in `python/paramgen.py` and
`dashboard/static/js/paramspec.js`; engine lerp in `bopos.py`; simfleet parity;
catch-up; take-over; int quantisation; browser-free tests; wire the preset apply
core's timed path to emit `morph` for generator entries.
