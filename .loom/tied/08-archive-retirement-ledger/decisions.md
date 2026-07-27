# Decisions — archive retirement ledger

## Final classification

The archive closes under an exhaustive default:

- selectively promoted durable properties have named living owners under
  `tests/`;
- explicitly listed reversed rulings are superseded;
- real timing, audio, Raspberry Pi, Pure Data, and fleet-adoption claims are
  environment/hardware evidence with named follow-ups where work remains;
- every other tied guard is retired authoring/integration evidence.

Promotion applies to the durable assertion, not to the archived script. The
189 scripts in 174 families remain preserved and unmodified. There is no
unowned archive-maintenance follow-up and no `tools/guard-sweep.sh`.

Active guidance in `CLAUDE.md` and `docs/VERIFICATION.md` now points routine
work at `tools/run-tests.sh` and living `tests/` modules. The narrow
repair-in-place supersession rule remains only for an archived assertion
explicitly encountered and relied upon during unrelated work.

## Verification

Passed 2026-07-27:

```text
git diff --check
./tools/run-tests.sh fast
  Ran 182 tests in 1.319s — OK
```

The ledger's named living test files and named waiting follow-up directories
were checked for existence. No browser, hardware, Pure Data, audible, or
real-LAN behavior changed or required verification in this documentation and
workflow close-out.
