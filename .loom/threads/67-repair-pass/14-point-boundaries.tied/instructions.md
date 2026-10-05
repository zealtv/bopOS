# 14-point-boundaries

**Status:** ready
**Goal:** point authoring and `/pt` frames fail closed, and a finished path
goes quiet.

Evidence: `lore:2026-10-05-bopos-review-core-libs` F7, F10.

- **F7.** `dashboard/points.py` and `python/pointfield.py` throw on list
  falloffs, numeric `points`, infinite IDs/falloffs; accept ID `2**31`; and
  `/pt 0.9` truncates to an empty full frame that clears all points.
- **F10 (low).** A completed non-looping path keeps `points_loop` sending at
  25 Hz forever. Send one final endpoint frame, then stop; loops, orbits and
  bounces continue.

Done when: tests fail before and pass after; fast green.
