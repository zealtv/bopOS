# 3-peripheral-lifecycle

**Status:** blocked on `1-scan-transport` (uses its relay)
**Goal:** create, destroy and re-initialise a peripheral from the Device tab —
and **see whether it worked**.

## Defects this fixes (they exist with or without a UI)

1. **Failed creates are silent.** `io/main.py` replies `/io/error <name>
   no-bus|create-failed`, but only to the engine, and no patch routes it. On
   2026-08-05 Bob's create had the wrong type *and* wrong address; the only
   symptom was silence.
2. **Read errors log the wrong message, twice.** Pulling a LIS3DH gives, per
   poll:
   ```
   Error reading from LIS3DH at address 0x19
   Error reading tilt: a bytes-like object is required, not 'float'
   ```
   The second line is a `TypeError` inside the failure path. Should be one line:
   which peripheral, which address, bus didn't answer. (Doubles log rate to
   ~5.7 MiB/hour.) Check other `io_*.py` modules for the same shape.
3. **A reconnected LIS3DH is silently dead.** After replug, errors stop and
   `/io/report` still lists it, but the chip is back in power-on reset
   (`CTRL_REG1=0x07`, `STATUS=0x00`). `setup()` ran once at create and never
   again, so the bridge emits **frozen zeros at 10 Hz with no error**. Needs a
   re-init path: when a read-failure burst ends, re-run `setup()`. The bridge
   only sees "errors stopped", not "device came back".
   - Bob (2026-08-14): the LIS3DH is the installation's sensor on the pole
     cable, so it must work. Check other modules individually; don't generalise.
   - This is exactly the failure `i2c-cable-run-validation` in
     kite-choir-brains is trying to detect.

## Deliver

- **Create / destroy** from the dashboard via the relay, with the real result
  reported. `io/main.py` has no destroy verb — add one.
- **Registry as a reply**, not a `print()`: name, type, address, last-read ok.
- **`/io/error` surfaced** where the operator triggered the create.
- Fixes for defects 2 and 3.

## Settle in-stitch (unless `0a` already has)

- **Ownership:** likely v1 answer — dashboard creates are ephemeral test
  instruments that don't survive an engine restart, and the UI says so.
- **Type from address** as an editable suggestion (e.g. `ads1115` for
  `0x48–0x4b`). Would have saved the 2026-08-05 session.
- **Address override** — Bob's board is at `0x4b`, not the default `0x48`.

## Done when

- Browser journey against simfleet.
- Real create/destroy of the ADS1115 at `0x4b` on Ciro Toast, exercising the
  failure paths (no-bus, wrong address, wrong type).
- LIS3DH unplug/replug on Finn Jet produces real values afterwards, not zeros.
