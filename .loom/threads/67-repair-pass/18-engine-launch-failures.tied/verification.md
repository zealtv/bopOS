# Verification

Software fixtures only, on macOS, 2026-10-05.

- Before the launcher fix, run-context failure (42), record-active failure
  (43) and immediate engine exit (87, both engine branches) all returned 0
  and failed the new regression assertions.
- After the fix: `~/.venvs/bopos/bin/python -m unittest
  tests.test_manifest_boot` passed all 11 tests.
- `./tools/run-tests.sh fast` passed all 598 tests.
- `bash -n bash/start-engine.sh` and `git diff --check` passed.

The first focused run hit sandbox restrictions on the existing boot harness's
`/dev/fd` log pipes. The rerun outside the sandbox passed the existing boot
tests and exposed the expected launcher failures. Final checks completed
successfully. Services and audio commands were inert fixtures throughout.

No Pi, real JACK, audio engine, installer, sudo or systemctl was run. The
one-second survival check catches immediate death; it is not a readiness
protocol or ongoing supervision. Hardware checks are in `pi-check.md`.
