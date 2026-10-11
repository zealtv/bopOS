# Verification — 26-flaky-launch-pid-test (2026-10-12)

Run on Bob's MacBook Air (8 CPUs), venv `~/.venvs/bopos`, from `tests/`.
"Load" means 8 × `yes > /dev/null`.

## Cause (confirmed)

`bash/start-engine.sh` starts `jackd` in the background (lines 160–162), then
probes readiness with `jack_lsp` (line 178). The fixture's fake `jack_lsp`
answered "ready" immediately, without waiting for the fake `jackd` to do
anything. The `audio` case then makes the fake `audio_config.py` exit 43, and
the launcher's cleanup kills `JACK_PID`. If that kill landed before the fake
jackd's bash ran its first line (`echo $$ >> "$FIXTURE_ROOT/launched"`),
`launched` stayed empty and the assertion at line 237 saw `0 != 1`.

Confirmation: adding `sleep 0.3` before that `echo` (temporary, reverted)
made the test fail 5/5.

**Fixture-only, not a launcher race that matters on a Pi** (*from reading
the code, not a hardware run*): the real `jack_lsp` succeeds only once the
real jackd is serving, and the launcher's cleanup kills its own recorded
child PID whatever state it's in.

## Before the fix

| run | result |
|---|---|
| 40 × single test, under load | 31 pass, 9 fail (`0 != 1`, line 237) |
| 40 × single test, second batch | 37 pass, 3 fail (same) |

The second batch was meant to run unloaded, but the first batch's `yes`
processes were still running (`kill $(jobs -p)` didn't reach them), so it
ran under load too.

The solo-run `FAILED (errors=1)` seen on 2026-10-11 did not recur in these
80 runs; every failure was the `0 != 1` assertion. Not reproduced; cause
unknown.

## Fix

`tests/test_manifest_boot.py`, `EngineLaunchTests.setUp`: the fake `jack_lsp`
now reports ready only once `launched` is non-empty (the fake jackd has
started), polling every 20 ms for up to 5 s. The wait lives in the fake
because the tests set `BOPOS_JACK_START_TIMEOUT=0`, which gives the launcher
a single probe. `jack-timeout` and `jack-death` cases still fail the probe
immediately, as before.

## After the fix

| run | result |
|---|---|
| `sleep 0.3` injected before the fake jackd's `echo` (temporary, reverted) | 5/5 pass |
| `python -m unittest test_manifest_boot` | 11/11 OK |
| 50 × single test, under load | **50/50 pass** |
| `tools/run-tests.sh fast` | 620 tests OK |

An earlier 50-run attempt showed 50 load errors in 0.000 s. That came from
my own mistake: it ran in parallel with the delay-injection check, which was
swapping the test file at the time. It wasn't a test result, and I discarded
it.
