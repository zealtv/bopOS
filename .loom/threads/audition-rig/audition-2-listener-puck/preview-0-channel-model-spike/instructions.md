# preview-0-channel-model-spike

Prove the chosen `bopos.mix~` signal semantics before controller or UI
implementation. Bob owns all `.pd` work; agents provide a pure matrix model,
OSC/message fixtures, measurement scripts, and retained results.

## Bob jig

- Insert `[bopos.mix~ 2]` upstream of master in a temporary two-channel output
  jig. Production/bypass must preserve L→L and R→R exactly in shape and gain.
- Exercise **zero positions** (bypass), **one position** (co-located stereo),
  and **two positions** (two mono elements) with distinguishable input signals.
- Accept one complete indexed matrix frame and smooth gain changes without
  clicks. Bad count, arity, NaN, or out-of-range values fail safe to the last
  valid frame or bypass; never silence production output.
- Confirm the abstraction validates frames against its `2` creation argument
  and that the implementation has a credible `[bopos.mix~ N]` construction
  seam. Do not implement N>2 yet.

## Agent work

- Specify and test the controller-side matrix/frame model independently of PD.
- Treat the adapter creation argument as the sole channel-count authority;
  never derive it from position count or activity level.
- Define one-position stereo balance/width behavior and two-position mono
  constant-power behavior with bounded gains and 32-bit-PD-safe values.
- Retain exact PD messages, capture method, expected channel amplitudes, and
  Bob's audible observation in this stitch.

## Acceptance

Automated capture distinguishes bypass, stereo-at-one-position, and two-mono
positions; rapid matrix movement is click-free at the chosen smoothing time;
master remains downstream; malformed state is safe; and Bob confirms that the
one-position stereo image behaves musically before the control grammar freezes.
