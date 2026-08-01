# Ownership and wire design — result

The physical/execution ownership boundary is ratified and recorded in
`decisions.md`.

Key outcomes:

- three explicit owners replace the mutable-destination `fleet_mutations`
  concept: execution, physical, and host;
- physical and execution traffic continue to share the ratified UDP 6660
  framework port but use explicit Dashboard destinations;
- exact-device `mute` becomes positive Device enabled state:
  `/all/os/to <uid> enabled <0|1>` with
  `/os/enabled <uid> <device-enabled> <output-enabled>`;
- MUTE ALL remains `/all/os/mute`, follows master across Live, Simulation, and
  Patch Edit, and never changes persistent Device enabled state;
- execution transitions cannot replay physical assignment, administration, or
  Device enabled state;
- Finn Jet and the Dashboard migrate legacy persisted mute fields once, with no
  indefinite compatibility alias;
- the complete Devices-tab and linked single-device asset surface is classified
  and an eight-part mode/convergence acceptance matrix is fixed.

## Verification

Read-only implementation and contract surveys covered all current Dashboard
WebSocket sends, 68 Dashboard OSC call sites, and 97 current mute/state
references across Dashboard, node, simulator, audition, docs, and tests.

```sh
rg -n "ws\\.send\\(" dashboard/static/js/dashboard.js
rg -n "self\\.osc\\.(send|action|uid_action|uid_command|os_command|request|fetch|assign|set_device|send_master|set_param|fire_cue)|self\\.send\\(" \
  dashboard/server.py dashboard/osc_bridge.py
rg -n "device_enabled|device_muted|set_device_mute|/os/mute|fleet_muted|effective_mute" \
  dashboard python tools docs tests -g '!*.pd' -g '!dashboard/shows/**'
git diff --check
```

`git diff --check` passed. No runtime code, `.pd` file, network port, or hardware
state changed in this design stitch.
