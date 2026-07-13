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
- **Stage A — listener puck:** the chosen implementation is a bypass-safe private
  fixed-stereo matrix inside each existing engine output adapter (see
  `audition-2-listener-puck`). Distance uses the shared smooth falloff and heading
  supplies listener-relative stereo balance. A rear forward-bias term is deferred
  until the dashboard puck and an audible listening pass; it is not silently baked
  into the relay model. Positions remain dashboard-owned assignment state.
- **Stage B — later, optional:** binaural/HRTF per instance for real 6DOF. Note: with
  a SuperCollider engine (pi-zero-performance §11) this collapses to one scsynth with
  N synths and native spatialisation (ATK) — revisit staging if SC lands first.

Constraints / notes:
- Laptop CPU: N patches at Zero-2W complexity is light for a laptop; if it isn't,
  that's useful pi-zero-performance data.
- Compounding target: audition rig + `scene-sequencing` = full desk-based composition
  loop (write scene → trigger → hear the space → iterate). Design demos around that.

---
**2026-07-13 status:** Stage 0 and the whole listener-puck software stack are
**tied** (`preview-0..3`; `tools/audition.py` is the relay-launcher, uid
scheme `audition-<n>`). The old gating constraints are resolved history:
the port spike passed, heartbeat identity landed, uids (not IPs) correlate
devices — no `--sim` flag exists or is needed. The only remaining child is
`preview-4-mac-linux-audible-gate.waiting` (Bob's ears + both platforms).
Forward coupling: the ratified seats model (`.loom/tied/
dashboard-8-identity-sim-design/`, implementation deferred) makes the
dashboard spawn this rig itself as the Simulate mode, sending loopback-only
— audition CLI flags become that mode's API; don't change them casually.
