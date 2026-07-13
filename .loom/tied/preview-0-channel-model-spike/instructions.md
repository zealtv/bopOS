# preview-0-channel-model-spike

Current blocker: Bob has wired a pass-through `bopos.audition~` placeholder
inside existing `bopos.out~`; the next session should hand-hold the matrix math
and verification. `bopos.out~` remains the only public patch abstraction.

Prove the chosen `bopos.out~` audition semantics before controller or UI
implementation. Bob owns all `.pd` work; agents provide a pure matrix model,
OSC/message fixtures, measurement scripts, and retained results.

## Bob jig

- Extend the private `bopos.audition~` helper already wired after the production
  master/notification mix and before `dac~`. Production/bypass must preserve
  L→L and R→R exactly in shape and gain.
- Exercise **zero positions** (bypass), **one position** (co-located stereo and
  duplicated dual-mono), and **two positions** (two mono elements) with
  distinguishable input signals.
- Accept one complete indexed matrix frame and smooth gain changes without
  clicks. Bad count, arity, NaN, or out-of-range values fail safe to the last
  valid frame or bypass; never silence production output.
- Confirm fixed-stereo frame validation. Do not design or implement N>2 here.

## Agent work

- Specify and test the controller-side matrix/frame model independently of PD.
- Treat two audio channels as the fixed ABI. Position count selects bypass,
  co-located stereo/dual-mono, or two-mono behavior; never infer topology from
  activity level or channel correlation.
- Define one-position stereo balance/width behavior and two-position mono
  constant-power behavior with bounded gains and 32-bit-PD-safe values.
- Retain exact PD messages, capture method, expected channel amplitudes, and
  Bob's audible observation in this stitch.

## Acceptance

Automated capture distinguishes bypass, stereo and dual-mono at one position,
and two mono positions; rapid matrix movement is click-free at the chosen
smoothing time; production master behavior is unchanged; malformed state is safe; and Bob
confirms the one-position stereo image before the control grammar freezes.
