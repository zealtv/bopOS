# Handoff — single-device Assets workflow complete (2026-07-16)

This supersedes `.notes/handoff-2026-07-16-assets-11a-complete.md` as the
current launch note.

## Current state

- Seat-group workspace delivery is committed as `f797073`.
- Assets 11a, 11b, and their `11-assets-device-workflow` parent are tied. Loom
  has 126 tied stitches, 13 dropped stitches, no active claim, and stage 12
  dashboard live controls as the next accepted software step.
- OSC contract v1.6 exposes durable device asset inventory backed by a
  persistent, fetch-seeded node hash cache and simulator parity.
- The Assets tab now owns the accepted one-online-assigned-physical-device
  workflow: inventory-derived state, single-slot Send/Update/Remove, active
  patch warnings, visible guard reasons, and responsive touch layout. Devices
  retains only observation and an Assets hand-off; fleet rollout remains
  separately gated in `asset-fleet-distribution`.
- Asset slot content is Git-ignored; `assets/README.md` is the tracked operator
  guide and documents the repository boundary and safe deployment workflow.
- Focused verification passes 17/17 for 11b and 27/27 for 11a. Patches fleet
  regression passes 10/10 and group state/bridge passes 6/6. Exact stale legacy
  verifier boundaries are recorded in the two tied Assets results files.
- Assets 11a/11b production changes and this handoff are uncommitted. No `.pd`
  file changed.

## Next implementation session

1. Read `CLAUDE.md`, this handoff, and run `./.loom/loom.sh status`.
2. If Bob requests a checkpoint, commit the tied Assets workflow first.
3. Claim/resume `12-dashboard-live-controls` as the single integration point
   for flat/nested parameter controls targeting All, Group, or Seat.
4. Keep fleet asset rollout in `asset-fleet-distribution`; do not fold it into
   live controls.

## Verification caveats

- `bop000`, the installation LAN, physical iPad, audio engine, audible rig,
  large real transfers, and real SD-card cache-warm timing were not exercised.
- The running manually started dashboard process predates these Python changes;
  restart it before manual testing the Assets workflow.
