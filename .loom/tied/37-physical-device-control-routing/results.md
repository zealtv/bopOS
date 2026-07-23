# Physical-device control routing — outcome

The Dashboard now treats execution output and physical device administration
as separate control planes.

- Master, MUTE ALL, parameters, automation, cues, and points follow the active
  Live, Simulation, or Patch Edit execution target.
- Every OSC-backed Devices-tab action uses the physical LAN destination,
  independent of execution mode.
- Device enabled/disabled is persistent, positive, and independent of MUTE ALL.
- Mode transitions and Live restoration never replay Device enabled/disabled.
- Host-only alias and Forget operations remain wire-silent.
- Physical control stays on the existing framework UDP port; no dedicated port
  was added.
- OSC contract v1.10 replaces exact-device `mute` with
  `/all/os/to <uid> enabled <0|1>` and reports `device_enabled`, `mute_all`, and
  `output_enabled`.

The four tied stitches retain design decisions, focused verification, and
implementation evidence. Final living verification passed 28/28 backend tests
and 12/12 real Dashboard/Chromium mode-matrix checks. Python compilation,
JavaScript syntax checks, and `git diff --check` also passed.

Finn Jet has not been updated or exercised. Rig adoption and audible behavior
remain a separate hardware verification step. No `.pd` file changed.
