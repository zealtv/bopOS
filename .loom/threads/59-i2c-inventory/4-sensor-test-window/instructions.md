# 4-sensor-test-window

"Test this sensor for N seconds" on the Device tab: press the button on the
box, get back a verdict.

Anchored on `3-peripheral-lifecycle` — the thing being tested is a peripheral
the bridge has instantiated.

## What it does

Reproduce, as one operator action, the script that answered the question on
2026-08-05 (`../watch.py`, and the transcript in
`../session-2026-08-05-ciro-toast.md`):

- Sample the peripheral **on the device**, at the bridge's own rate, for a
  bounded window (the session used 90 s at 50 Hz; the default should be
  shorter — 10 s — with a longer option).
- Return **one summary**: per element, the resting value, min, max, swing, and
  a moved/idle verdict against a threshold; plus a count of edges and their
  timestamps.

The real output it has to match:

```
--- 90s window, 21 edge(s)
A0  rest 3.245  min -0.001  max 3.253  swing 3.254  <== MOVED
A1  rest 0.001  min  0.000  max 3.289  swing 3.288  <== MOVED
A2  rest 3.248  min -0.001  max 3.256  swing 3.257  <== MOVED
A3  rest 3.282  min  3.281  max 3.289  swing 0.008
```

## Second requirement, from Bob the same session

*"I also need to be able to see the values that would be received in PD so I
can patch appropriately."*

The summary above is in the peripheral's own units, which is a good start but
not sufficient — what he is patching against is a specific OSC message with a
specific address, argument count and order. So the window must also report the
payload **verbatim as the engine receives it**:

```
/adc 3.245 0.001 3.248 3.282        ← exactly what [route adc] sees
```

Concretely, that means reporting: the message address (which is the peripheral
*name* given at create time, not its type — `io create adc ads1115 0x4b`
yields `/adc`), the argument count and order, and the units. `io/main.py`
flattens a dict peripheral's `read_data()` by `.values()` order and a list's
by index (`python/io/main.py:96-107`), so **the argument order is an
implementation detail of the module** and is exactly the thing an operator
cannot discover from the outside. Report it, don't make them read the source.

Since the capture is a bounded window, it can carry a **recorded trace** — the
actual frames, at the poll rate — and still be one reply, not a stream. 10 s at
20 Hz is 200 frames; that is a payload, not telemetry. Give the trace as
frames of PD-shaped arguments, so the operator can read rest values, press
values, bounce and settling time straight off it and set thresholds from
measured numbers. Decide the trace's size cap and what happens past it
(decimate, or refuse a window longer than N seconds).

## Why a window and not a live readout — do not quietly reverse this

- **It is the question being asked.** "Am I getting button presses" is about
  an interval. A live needle makes the operator watch and press at once, and
  says nothing about the press they missed.
- **The contract forbids the streaming version.** §6: there is no streamed
  telemetry and no framework meter plane — `meter_loop`, the `/rpt` echo chain
  and `role: "meter"` were deleted rather than renamed, and the *leased* probe
  (`… <hz> <ttl>`) was proposed at the v1.2 engine-boundary ratification and
  deliberately **not** adopted. A bounded capture returning one summary
  reopens none of that. A live readout is a Bob-gated argument to reverse a
  ratified decision; if this stitch finds itself wanting one, that is a
  proposal, not an implementation.
- **The rest column carries information a needle loses.** On Ciro Toast A1
  rested at 0 V and rose while A0 and A2 rested at rail and fell. The
  inversion is obvious in a rest/swing table and invisible in three numbers
  twitching.

## Shape

- The reply is **late** — 10 s after the request — so it cannot ride the
  synchronous request/reply idiom unexamined. Decide how the dashboard learns
  the window has closed, and what it shows meanwhile.
- The bridge is polling its peripherals for the engine at the same time. The
  capture must ride the **existing poll loop**, not open a second reader on
  the same chip.
- One window at a time per device; say what happens if a second is requested.
- Threshold for "moved" is per-peripheral-kind, not universal — 0.5 V is
  meaningful for an ADC and meaningless for MPR121 touch counts.

## Verify

Simfleet needs a fake peripheral that can be made to "move" so the summary is
testable headlessly, including the idle case — a test that only checks the
moved verdict passes vacuously on a dead sensor. Then the real gate: press the
button on Ciro Toast's ADS1115 at `0x4b` and get a three-moved, one-idle
verdict back in the browser.
