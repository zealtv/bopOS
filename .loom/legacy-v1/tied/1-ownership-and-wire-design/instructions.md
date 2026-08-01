# 1-ownership-and-wire-design

Ratify the ownership matrix and replacement wire/state vocabulary before code
changes.

- Inventory every command reachable from the Devices tab, including physical
  patch diagnostics and linked single-device asset operations.
- Classify Dashboard commands as execution-target, physical-device, or
  host-only state. Remove the current broad `fleet_mutations` concept from the
  design.
- Specify positive Device enabled/disabled request, acknowledgement, report,
  persistence, boot, reconnect, and mismatch-convergence semantics.
- Keep MUTE ALL as an execution-target control analogous to master, including
  Simulation and Patch Edit behavior.
- Specify exactly what `restore_live_state()` may replay; it must not replay
  physical-device state.
- Choose the wire migration for Finn Jet and identify compatibility cleanup in
  Dashboard, `bopos.py`, simfleet, audition, contract/reference docs, and
  persisted host/node state.
- Record decisions and acceptance checks in this stitch before implementation.

Do not edit `.pd` files. No new UDP port is expected.
