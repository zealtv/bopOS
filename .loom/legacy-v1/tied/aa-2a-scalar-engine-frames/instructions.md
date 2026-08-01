# aa-2a-scalar-engine-frames

Correct the engine-boundary mistake exposed by the real audible gate.

Bob clarified that bopOS owns ramp evaluation and Pd must continue receiving
scalar `/p/*` values. The current ratified text and `paramgen.py` instead send
float `[target, duration_ms]` pairs, which Pd distributes across multi-inlet
parameter consumers. In `demo-pd`, the first `1 5000` fade frame overwrites a
`[clip]` bound and produces the observed persistent extreme synth gain.

- Make every `GeneratorEngine` emission a one-element numeric list. Evaluate
  float fades/loops/LFOs at the existing ~33 Hz control tick; retain exact int
  crossing semantics, phase behavior, current-value catch-up, last-message
  wins, and plain scalar byte behavior.
- This is shared code: production bopos, simfleet, and audition must all adopt
  it without an audition-only branch.
- Amend OSC contract §3.2 to state that bopOS decomposes all generators to
  selector-free scalar engine frames. No new address or Pd edit.
- Add focused regression proving fades and every float LFO frame are scalar,
  bounded in the authored range, progressive, replaceable, and cleanly shut
  down; also prove audition loopback engine datagrams never contain a duration.
- Run the shared automation, audition, and managed catch-up regressions that
  remain applicable. Record the originally ratified pair behavior as
  superseded by Bob's 2026-07-20 audible ruling, not as a Pd obligation.

Never edit `.pd` files.
