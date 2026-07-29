# Verification

## Diagnosis

### Control-surface enum probe

The production control was sound. The verifier wrote `value` on one queried
`<select>`, then queried again to dispatch `change`. A heartbeat render could
replace the element between those operations, so the handler saw the old value
or no new `mode` send. The probe now waits for `onchange` and uses the same
live, handler-bound element for both the write and dispatch.

### Generator Stop

This was a production boundary bug, not buffered simfleet output. Simfleet
flushes each emitted tick, and temporary receipt instrumentation showed zero
Stop commands while both device generators continued at their expected tick
rate. The dashboard had parsed `["stop"]` and cleared its automation mirror,
then `preset_application.canonicalize_args()` treated the singleton string as
a numeric durable scalar and returned `None`. The OSC bridge consequently did
not put a valid Stop on the node wire.

`canonicalize_args()` now preserves the already-validated singleton Stop
command. A durable unit regression pins that boundary, while the browser
journey continues to prove that real dashboard → OSC → simfleet traffic stops
both agreeing and mixed-target generators.

## Commands and results

- `python -m py_compile` on all four touched Python files: pass.
- `tests/test_preset_application.py`: 24 tests, pass.
- `tests/verify_generator_drawer.py`: 3 consecutive full runs, pass. Each run
  covered both agreeing and mixed targets and asserted that ticks genuinely
  cease after Stop.
- `tests/verify_control_surface_component.py`: 5 consecutive full runs, pass.
- `./tools/run-tests.sh fast`: 250 tests, pass.
- `./tools/run-tests.sh browser`: 17/17 browser journeys, pass.
- `git diff --check`: pass.

## Boundaries

No physical node, Pure Data patch, installation LAN, audible output, iPad, or
touch hardware was exercised. The Stop path was verified through the real
dashboard server and OSC bridge into simfleet's real `GeneratorEngine`; actual
node/PD adoption remains outside this software-only stitch.
