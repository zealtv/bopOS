# 4-sensor-test-window

**Status:** blocked on `3-peripheral-lifecycle`
**Goal:** "test this sensor for N seconds" on the Device tab → one verdict, plus
the exact values PD will receive.

Replaces `../watch.py` from the 2026-08-05 session.

## Output 1 — verdict

Sample on the device at the bridge's rate for a bounded window (default 10 s,
longer option). Per element: rest, min, max, swing, moved/idle; plus edge count
and timestamps. Target shape:

```
--- 90s window, 21 edge(s)
A0  rest 3.245  min -0.001  max 3.253  swing 3.254  <== MOVED
A1  rest 0.001  min  0.000  max 3.289  swing 3.288  <== MOVED
A3  rest 3.282  min  3.281  max 3.289  swing 0.008
```

## Output 2 — what PD sees

Bob: *"I also need to be able to see the values that would be received in PD so
I can patch appropriately."* Report the payload verbatim:

```
/adc 3.245 0.001 3.248 3.282        ← exactly what [route adc] sees
```

- Address = the peripheral's *name* from create (`io create adc ads1115 0x4b` →
  `/adc`), plus argument count, order and units.
- Argument order is an implementation detail of each module (dict `.values()` /
  list index) — report it so nobody reads source.
- Include a recorded trace (e.g. 200 frames for 10 s at 20 Hz) — one reply, not a
  stream. Decide a size cap and what happens past it.

## Why a window, not a live readout — don't reverse this quietly

- It answers the actual question ("am I getting presses?") over an interval.
- Contract §6 forbids streaming telemetry; a live readout would need a Bob-gated
  proposal.
- Rest values reveal per-channel polarity (A1 rests low, A0/A2 rest high) that a
  twitching needle hides.

## Design points

- Reply arrives ~10 s late — decide how the dashboard learns it's done and what
  it shows meanwhile.
- Ride the existing poll loop; no second reader on the chip.
- One window per device at a time; say what a second request does.
- "Moved" threshold is per peripheral kind.

## Done when

- simfleet fake peripheral that can move, testing both moved **and idle**
  verdicts.
- Hardware: press the button on Ciro Toast's ADS1115 at `0x4b` → three moved, one
  idle, in the browser.
