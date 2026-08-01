# 37-physical-device-control-routing

Separate execution-target traffic from physical-device control.

Bob's 2026-07-23 rulings:

- Master, MUTE ALL, parameters, automation, cues, and points target the active
  execution mode: Live, Simulation, or Patch Edit.
- Everything presented on the Devices tab targets a physical device, regardless
  of execution mode. Host-only alias/registry changes still describe that
  physical UID.
- The persistent per-device control is **Device enabled/disabled**, distinct
  from MUTE ALL.
- Entering or leaving Simulation/Edit must never change or replay Device
  enabled/disabled.
- Physical control remains on the existing framework LAN plane; do not add a
  dedicated port merely to separate Dashboard routing.
- Finn Jet is the only deployed device. Wire and persisted terminology may be
  migrated for clarity instead of retaining the exact-device `mute` vocabulary.

Outcome: explicit execution and physical routes, unambiguous Device enable
state, and a living mode-matrix regression that prevents either plane leaking
into the other.
