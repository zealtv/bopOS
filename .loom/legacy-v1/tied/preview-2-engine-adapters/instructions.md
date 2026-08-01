# preview-2-engine-adapters

Integrate the tied private `/audition/matrix <l0> <l1> <r0> <r1>` frame into
the PD and SuperCollider engine adapters. Bob owns and audibly verifies all PD
edits; agents implement SC, static/behavioral gates, and retained results.

## Pure Data

- In `pd/bopos.pd`, route selector-stripped `audition matrix ...` messages from
  the existing local engine ingress to `s bopos-audition-matrix`.
- Do not change the public `bopos.out~` ABI or the proven private DSP. Normal
  production startup remains identity bypass. Unknown/malformed messages must
  not reach or disturb the matrix receiver.
- Verify locally with exact engine-port OSC frames, not only a same-canvas send:
  valid frames move the image; malformed arity/type/range retains the last valid
  frame; ordinary `/id`, `/os/master`, `/p`, `/pt`, `/cue`, and `/notify` routes
  remain unchanged.

## SuperCollider

- Extend the existing final `boposOut` stage in
  `templates/supercollider-bopos/main.scd` with the same fixed-stereo equations
  and 20 ms gain smoothing used by the tied model.
- Install a private `/audition/matrix` OSCdef on `BOPOS_ENGINE_PORT`. Accept
  exactly four finite numeric gains in `[0,1]`; reject malformed state and retain
  the last valid identity/matrix. Master remains a separate smoothed final
  multiplicand and patch params remain patch-owned.
- Update the template README and add a focused static/behavioral verifier. Run
  `sclang` syntax/runtime checks when available; otherwise state that boundary
  honestly and retain deterministic model/static evidence.

## Acceptance

- PD and SC spellings exactly match the tied private frame.
- Identity, one-position, and two-position fixture coefficients match the pure
  controller model; rapid updates are smoothed; malformed state cannot mute.
- Focused adapter verification, tied preview-0/preview-1 regressions, compilation,
  and `git diff --check` pass. Record exact commands and all unverified audible,
  macOS/Linux, PD, or SC-runtime boundaries before tying.
