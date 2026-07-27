# 02-osc-and-manifest-contract-tests

Promote durable OSC wire and manifest-schema assertions into living tests.

- Start from `01`'s matrix and the ratified `docs/OSC-CONTRACT.md`; do not
  re-litigate the contract.
- Audit existing `tests/` coverage before mining tied guards.
- Deduplicate and re-express only invariant grammar, validation, routing, and
  run-context properties against current production helpers.
- Keep protocol simulation honest: any changed protocol behavior must be
  represented in `tools/simfleet.py` in the same stitch.
- Separate fast contract tests from any necessary browser/integration verify.

Run the focused living tests and record exact results. No `.pd` edits and no
maintenance of superseded tied assertions.
