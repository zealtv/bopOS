# 13-generator-correctness

**Status:** ready
**Goal:** `python/paramgen.py` keeps contract §3.3: explicit-start loops loop,
integer generators never miss a crossing, and work stays bounded.

Evidence: `lore:2026-10-05-bopos-review-core-libs` F4, F5, F6.

- **F4.** `['loop', 0, 1, '1s']` parses as a one-shot fade.
- **F5.** `_crossings` compares only the previous and current samples, so
  reversals inside a tick and loop-boundary segments drop crossings.
- **F6 (high).** Huge duration strings parse to infinity; fades preallocate one
  event per ~30 ms at apply time under the lock (120 billion for
  `1000000h`); big int jumps materialise the whole crossing range.

Advance piecewise through segment boundaries and compute ticks lazily; the
fixes share code, so do them together. Any new public limit (duration, range)
goes to Bob first. Done when: deterministic tests for each case; fast green.
