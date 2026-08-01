# Decisions — living-suite runner

## Stable entry point

`tools/run-tests.sh` implements the child `01` contract:

- no argument defaults to `fast`;
- `fast` runs unittest discovery only under `tests/test_*.py`;
- `browser` runs each `tests/verify_*.py` in lexical order and a fresh Python
  process, continues after failures, and prints a final per-file summary;
- `all` runs both tiers and returns nonzero if either tier fails;
- invalid tiers and extra arguments return usage status `2`;
- `BOPOS_PYTHON` overrides the documented
  `~/.venvs/bopos/bin/python`;
- a missing interpreter prints the existing venv setup guidance;
- the runner changes to the repository root, sets
  `PYTHONDONTWRITEBYTECODE=1`, preserves verifier output, and never discovers
  `.loom/tied/`.

The runner uses Bash only as an orchestrator for the two established Python
invocation styles. It creates no logs or temporary runner artifacts.

## Actionable orchestration coverage

`tests/test_test_runner.py` invokes the real shell runner with a temporary fake
Python executable. It proves:

- default and arbitrary-caller-directory behavior;
- the exact fast discovery boundary and bytecode environment;
- usage and missing-Python failures;
- browser continuation after a middle verifier fails;
- complete PASS/FAIL summary and nonzero browser status;
- `all` still reaches browser tests after fast failure and retains failure.

Using a fake interpreter keeps this living test inside the fast tier without
recursively launching the fast suite.

## Pre-tie and CI wiring

`docs/VERIFICATION.md` now names `./tools/run-tests.sh fast` as the routine
pre-tie command, documents `browser` and `all`, states that durable tests live
under `tests/`, and keeps hardware-only adoption outside software pass claims.

There is no `.github/` directory or other checked-in CI workflow. Per child
`01` and this stitch's instructions, no external CI service, workflow,
credential, or placeholder was invented.

## Hardware boundary

The runner's software tiers deliberately exclude hardware, Pure Data, audible
output, real-LAN, and iPad adoption. The browser tier uses local TCP/UDP ports
and headless Chromium; a green browser summary is software integration
evidence, not installation-rig acceptance.
