# 4-sensor-test-window

**Status:** waits on `3-peripheral-lifecycle` · `0a` may fold this into live
streaming (`6`) — check its ruling first
**Goal:** "test this sensor for N seconds" on the Device tab → one verdict per
channel, plus the exact values the patch will receive.

Written to replace `../watch.py` (2026-08-05), when live streaming was off the
table. Bob's 2026-10-03 ask for live values changes that; keep this only if a
summary over a window still answers something a live view doesn't.

## What it answered that a live view might not

- "Am I getting presses?" over an interval — rest, min, max, swing, moved/idle
  per channel, plus edge count:
  ```
  --- 90s window, 21 edge(s)
  A0  rest 3.245  min -0.001  max 3.253  swing 3.254  <== MOVED
  A1  rest 0.001  min  0.000  max 3.289  swing 3.288  <== MOVED
  A3  rest 3.282  min  3.281  max 3.289  swing 0.008
  ```
- **Rest values show per-channel polarity** (A1 rests low, A0/A2 rest high),
  which a flickering number hides.
- **What the patch sees, verbatim** — Bob: *"I also need to be able to see the
  values that would be received in PD so I can patch appropriately."* e.g.
  `/adc 3.245 0.001 3.248 3.282`: address = the peripheral's create name,
  argument count, order and units. Order is each module's implementation
  detail — show it so nobody reads source. (Any live view in `0a` must cover
  this too.)

## Done when

- simfleet fake peripheral that can move, testing both moved and idle.
- Hardware: press the button on Ciro Toast's ADS1115 at `0x4b` → three moved,
  one idle, in the browser. Separate claim.
