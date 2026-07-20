# aa-2-audible-simulation-gate

Adopt the repaired relay in the real Dashboard-managed audible Simulation
workflow after `aa-1-audition-generator-parity` is tied.

1. Run the current Dashboard with Simulation targeting a real host patch and
   its normal engine processes (macOS/CoreAudio is the primary gate).
2. Exercise a deterministic fade and LFO on manifest-declared numeric
   parameters of an online virtual Seat. Prefer the saved `test` show's `go`
   step when its patch provides a continuously audible signal; otherwise use a
   purpose-built show/patch already in the repository. Do not edit Pd.
3. Confirm by ear that the audible output follows both generators, and confirm
   the Dashboard marker/fade thumb remains consistent with that behavior.
4. Confirm take-over with a plain slider value stops the audible generator,
   Simulation stop cleans up every child engine/generator thread, and switching
   back to Live fleet restores the prior target without leaking automation.
5. Run the adjacent managed-Simulation transition and parameter-catch-up
   regressions selected via `docs/VERIFICATION.md`.

Record OS, audio backend, patch/show, exact commands, observed result, and any
limitation. If the software checks pass but an audible engine or human listening
gate is unavailable, mark this stitch waiting with the precise gate rather than
claiming audible success.
