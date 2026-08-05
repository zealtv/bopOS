# 2-device-tab-inventory

Render the connected I2C addresses on the Device tab, alongside the facts the
report already shows.

Anchored on `1-scan-transport` (`needs/`): the transport and reply shape are
that stitch's ruling, not this one's.

## What it says

- **Addresses, honestly.** Hex, sorted, one row or one line of chips —
  `0x18  0x48  0x5A`. A well-known-address hint may be shown *as a hint*
  (`0x5A · MPR121?`), never as an identification; `sys_i2c.py`'s docstring is
  the standing rule — the bridge does not know device types from addresses.
- **The three states are different.** No bus (`has_i2c` false), bus present
  and empty, and not-yet-scanned are three distinct things and must read as
  three distinct things. A blank space is not "nothing attached".
- **Kernel-claimed addresses.** `sys_i2c` reports `EBUSY` addresses as
  present — i2cdetect's `UU`. On a HiFiBerry node the DAC is one of these, so
  the list will contain an address the operator did not attach. Decide whether
  that is annotated or just listed, and record the call.
- **Demand-driven, if `1` made it so.** If the scan is a probe rather than a
  report field, this needs a trigger and a "last scanned" reading — the report
  section's existing refresh idiom is the reference, not a new pattern.

## Where

`dashboard/static/js/dashboard.js:1746` is today's whole report surface: one
`<dl>` built from a fixed key list, with `has_i2c` already in it. The
inventory belongs beside it. Match the shipped component set — this tab has
been through `desktop-ui-overhaul`, so no new bespoke chrome, no new
stylesheet, and §12 applies (`--bg` is ground, never a panel colour).

## Verify

Browser journey extending the nearest living `tests/verify_*.py` on the Device
tab, driven by the simfleet fake address list `1` adds. Cover all three states
above; a test that only asserts the populated case passes vacuously on a
device with no bus. Real hardware — an actual peripheral appearing and
disappearing on the Finn Jet / Ciro Toast rig — is a hardware adoption check;
say so in `verification.md` rather than claiming it.
