# 2-device-tab-inventory

**Status:** blocked on `1-scan-transport`
**Goal:** show the connected I2C addresses on the Device tab.

## What it shows

- **Addresses:** hex, sorted (`0x18  0x48  0x5A`). A known-address hint is OK
  *as a hint* (`0x5A · MPR121?`), never as identification.
- **Three distinct states:** no bus (`has_i2c` false), bus but empty, not yet
  scanned. Blank must never mean "nothing attached".
- **Kernel-claimed addresses** (`UU`, e.g. the HiFiBerry DAC) will appear.
  Decide: annotate or just list. Record it.
- If `1` made the scan on-demand: a trigger + "last scanned", using the report
  section's existing refresh pattern.

## Where

Beside the report `<dl>` in `dashboard.js` that already shows `has_i2c`. Use the
shipped component set — no new stylesheet; §12 applies.

## Done when

- Browser journey (extend the nearest Device-tab `tests/verify_*.py`) using `1`'s
  simfleet address list, covering **all three states**.
- Real peripheral appearing/disappearing on the rig is a hardware check — say so
  in `verification.md`, don't claim it.
