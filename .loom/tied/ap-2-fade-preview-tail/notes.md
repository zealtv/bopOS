# ap-2 notes

## Diagnosis

`ParamSpec.shapeFraction` wraps phase modulo 1 — correct for periodic
LFOs, but both one-shot ramp samplers fed it `fraction = 1` at each
segment's final sample: `saw(1)` wraps to `0`, so the last sample of
every fade/loop segment collapsed back to the segment's *start* value.
That is exactly Bob's screenshot: a single-segment fade rendering as a
rising line with a sharp "release" drop at the right edge.

Two call sites had the identical bug:

- `show.js` (~589) — the Show-inspector SVG preview (Bob's report);
- `facilitator.js` (~147) — the live **loop** marker's CSS `linear()`
  easing, where every segment boundary sample regressed to the segment
  start, distorting the moving marker the same way.

## Fix

At both call sites: `fraction >= 1 ? 1 : shapeFraction("saw", …)` with a
comment naming the wrap. `shapeFraction` itself is untouched — periodic
users depend on the wrap.

## Verify

`verify_fade_preview_tail.py` (house pattern, real server + simfleet +
headless Chromium):

- one-segment fade 0→1/5s: preview path time-monotonic, value
  never decreases, ends at the destination, spans the full axis;
- two-segment fade 1/5s → .5/5s: midpoint boundary reaches 1.0, end sits
  at .5;
- facilitator loop marker: `linear()` easing's 50% boundary sample holds
  segment one's destination (.8), not the wrapped start;
- no console errors. Screenshots: `preview-one-segment.png`,
  `preview-two-segments.png`.

Run: `~/.venvs/bopos/bin/python verify_fade_preview_tail.py` →
**All fade preview tail checks passed** (10 checks), 2026-07-20.
Negative test: with the two fixes stashed, 5 checks fail exactly on the
wrap symptom (last sample 0.0) — the suite bites.
