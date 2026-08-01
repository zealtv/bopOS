# 11-browser-test-failures

Repair the two browser-suite failures surfaced while verifying
`09-show-integration/2-preset-messages`. **Needs
`10-venue-preset-retirement` tied** so this is the final post-replacement
guard cleanup for thread 41.

Both failures reproduce unchanged on pre-`2-preset-messages` commit
`66d9ad1`; see `.loom/tied/2-preset-messages/verification.md`. Do not attribute
them to preset-message code, and do not weaken assertions merely to make the
suite green.

## Failures

1. `tests/verify_control_surface_component.py` —
   `choosing an enum option sends its integer index` reads the previous send.
   The probe currently writes one queried `<select>` and dispatches `change`
   on a second query; a re-render can make those different elements despite
   the existing anti-flake comment. Make the journey exercise one live,
   handler-bound enum control and assert its `mode` send deterministically.
2. `tests/verify_generator_drawer.py` —
   both agreeing and mixed journeys report that density ticks continue after
   Stop (`~20 → ~110 → ~170`) even though dashboard automation clears.
   Diagnose whether Stop is failing at the node/simfleet boundary, is racing
   delivery, or the verifier is counting buffered/old output. Fix the owning
   behavior if real; fix the measurement only if the wire/node behavior is
   already correct. Retain an assertion that ticks genuinely cease.

## Verify and tie

- Reproduce each journey alone before changing it.
- Add the narrowest durable regression for any production behavior changed.
- Run both isolated browser journeys until stable across repeated runs.
- Run `./tools/run-tests.sh fast` and `./tools/run-tests.sh browser`; both
  tiers must be green.
- Record the diagnosis, commands, pass counts, and non-software boundaries in
  this stitch before tying. Then assess and tie the `41-preset-primitive`
  parent if `10` and every other child are tied.
