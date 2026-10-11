# 26-flaky-launch-pid-test

**Status:** ready (added 2026-10-11, Bob asked for it first in the queue)
**Goal:** `test_manifest_boot.EngineLaunchTests.test_record_active_failure_stops_jack_before_engine`
passes reliably, so the pre-commit fast suite stops refusing unrelated commits.

## Evidence (2026-10-11)

- The fast suite failed this test twice in a row under pre-commit:
  `AssertionError: 0 != 1` at `self.assertEqual(len(self.launched_pids()), 1)`
  (`tests/test_manifest_boot.py:237`). The same suite passed 620/620 earlier
  that session.
- Run alone five times: 4 × OK, 1 × `FAILED (errors=1)` (an error, not a
  failure; traceback not captured, so a second failure mode may exist).
- Commit `3403144` (lore/glean Markdown only) went in with `--no-verify`
  at Bob's OK because of it.
- The test came in with `a9354e0` (2026-10-05, `18-engine-launch-failures`).

## Hypothesis (unverified)

The fake `bin/jackd` records itself with `echo $$ >> "$FIXTURE_ROOT/launched"`
as its first line. `start-engine.sh` starts jack in the background, then
the `audio` case makes `audio_config.py` exit 43 and the launcher stops
jack. Under load, the stop can land before the fake jackd's bash has run its
`echo`, so `launched` stays empty. Check the launcher's order before
trusting this.

## Done when

- Root cause confirmed (reproduce under load, e.g. a loop of the single test
  or the full fast suite repeated), including what the solo-run *error* was.
- Fix lands in the test fixture, unless the evidence shows the launcher
  itself races in a way that matters on a Pi — then write that up and stop
  before changing launcher behaviour.
- The test passes in a repeat loop (say 50 runs) and in `tools/run-tests.sh
  fast` from `~/.venvs/bopos`.
