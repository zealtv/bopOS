# audition-rig

**Goal:** *hear* the fleet without hardware — N real engine instances running a given
patch on the laptop, spatially monitored from a listener perspective. Primarily a
**composition tool**: the pain it kills is composing "deaf" (needing all Pis set up to
hear a piece). Review §12.

Architecture: not simulated audio — the actual patch, N times, on the real control
plane. `simfleet.py` (dashboard-0-sim-fleet) simulates *protocol-only* devices; the
audition rig runs *audible* instances. Same fleet-shape, two fidelities — keep flags/
config compatible so they can mix (e.g. 3 audible + 20 protocol-only).

Stages (each independently useful — Bob confirmed Stage 0 alone has value):

- **Stage 0 — all-at-once:** launcher (`tools/audition.sh` or part of simfleet) starts
  N × `pd -nogui -jack -jackname sim-pi-<n>` each opening the target patch with its
  own device ID (reuse the start.sh `-send` startup-message mechanism); jack script
  sums all outputs to stereo out. Done = a patch + scene plays audibly on the laptop
  as N devices, controlled from the dashboard.
- **Stage A — listener puck:** small Python jack client (`tools/spatial_monitor.py`)
  holding an N×2 gain matrix; per-instance gain = falloff(distance(listener, device))
  × forward bias (dot of listener heading · direction-to-device). Listener = draggable
  puck (position + heading) on the dashboard spatial map; puck state reaches the
  monitor over the dashboard WebSocket or a local OSC port. Positions come from
  `installation.json` — same data `spatial-audio` uses, so compositions are auditioned
  with the exact falloff math that later drives real `/gain` automation.
- **Stage B — later, optional:** binaural/HRTF per instance for real 6DOF. Note: with
  a SuperCollider engine (pi-zero-performance §11) this collapses to one scsynth with
  N synths and native spatialisation (ATK) — revisit staging if SC lands first.

Constraints / notes:
- Child `audition-0-port-spike` MUST pass before building anything (single-host UDP
  broadcast port sharing is the load-bearing assumption).
- Single-IP consequence: all instances share the laptop IP, so IP-based device
  correlation breaks — depends on heartbeat-with-identity (`osc-schema-contract`).
  Until that lands, the dashboard can special-case a `--sim` flag; don't build
  elaborate workarounds.
- Laptop CPU: N patches at Zero-2W complexity is light for a laptop; if it isn't,
  that's useful pi-zero-performance data.
- Compounding target: audition rig + `scene-sequencing` = full desk-based composition
  loop (write scene → trigger → hear the space → iterate). Design demos around that.
