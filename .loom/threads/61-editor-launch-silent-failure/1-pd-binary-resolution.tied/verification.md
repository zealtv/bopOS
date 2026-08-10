# verification — 1-pd-binary-resolution

## Ran

- `tests/test_pd_binary_resolution.py` — 11 new browser-free tests, all green.
  Every resolver case runs against a fabricated `/Applications`-shaped tmpdir,
  so none of them assert the developer's machine: numeric-not-lexicographic
  sort (`0.9-1` / `0.55-2` / `0.55-10` / `0.56-2`), non-Pd and malformed entries
  ignored, missing app dirs ignored, highest bundle preferred, non-executable
  bundle skipped, explicit `--pd-bin` wins, no candidates → `None` rather than a
  literal, Linux resolves through `PATH`, the argparse default is `None`, the
  named preflight error contains both the path tried and `--pd-bin`, resolution
  is cached, and `--no-engine` neither resolves nor loads a patch.
- `./tools/run-tests.sh fast` — **Ran 309 tests, OK.**
- Failure path end to end:
  `tools/audition.py --pd-bin /no/such/pd` exits 1 with
  `PdBinaryError: no usable Pure Data executable: tried /no/such/pd; bundles
  seen: /Applications/Pd-0.55-2.app/…/pd; pass --pd-bin to name one` — raised
  before `send_ready()`, as intended.
- Happy path end to end: `tools/audition.py --devices 1 --audio-backend none`
  with no `--pd-bin` resolved the installed bundle, launched real Pd, and the
  patch printed its `bopos-context` lines. Still running at 6s; killed.

## NOT run, and why

- **The affected machine.** This session's machine carries exactly one bundle,
  `Pd-0.55-2.app` — the very build the old literal named — so it could never
  have reproduced Bob's failure and cannot prove the fix on the machine that
  had it. The multi-bundle preference is proven only by the fabricated-tmpdir
  tests. Bob's machine (`0.55-0` + `0.56-2`) should now pick `0.56-2`;
  *Launch editor* reaching and **holding** `running` there is the outstanding
  adoption check.
- **The stopgap symlink removal** named in the instructions: no symlink was
  made on this machine (the bundle is a real directory, `drwxr-xr-x`, dated
  2024-11-17), so there was nothing to remove. If one was made on Bob's
  machine it must still be removed before the adoption check means anything —
  it is the exact condition under which this stitch passes while changing
  nothing.
