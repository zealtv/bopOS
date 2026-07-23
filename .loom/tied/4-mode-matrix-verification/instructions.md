# 4-mode-matrix-verification

Add durable regression coverage organized under the living `tests/` suite.

- Exercise distinct physical-LAN and audition receivers in Live, Simulation,
  and Patch Edit.
- Prove every OSC-backed Devices-tab action reaches only the physical route in
  all three modes.
- Prove master and MUTE ALL reach only the active execution route and both work
  during Patch Edit.
- Prove entering/leaving modes emits no Device enabled/disabled command.
- Prove explicit enable/disable, reconnect convergence, acknowledgement,
  persistence, boot behavior, and mismatch repair.
- Cover host-only Device alias/forget operations without inventing wire
  traffic.
- Run the focused browser/backend checks plus adjacent OSC-contract and
  simulation-transition regressions required by `docs/VERIFICATION.md`.

Record exact commands, pass counts, and any Finn Jet hardware boundary.
