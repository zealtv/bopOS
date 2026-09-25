# Handoff — Seat groups complete (2026-07-16)

This supersedes `.notes/handoff-2026-07-16-seven-stage-sweep.md` as the current
launch note.

## Current state

- Seat-group core was committed as `5c43d9b` (`Implement Seat group core`).
- Seat-group delivery, the top-level `seat-groups` goal, and the post-delivery
  Seat-group UI revisions are tied. Loom has 123 tied stitches, 13 dropped
  stitches, no active claim, and Assets 11a as the next software loose end in
  the accepted sweep.
- Delivery production changes remain uncommitted: Groups authoring in Seats,
  both membership checklist directions, Lucide-derived eye/eye-off layer
  controls, stable four-slot spatial rails, legend/focus/clear/empty behavior,
  accessibility/touch work, third-party notice, verification, and this note.
- The focused real-browser delivery verifier passes 20/20 checks, including a
  dense 100-Seat fixture, measured graphical contrast, 44px hit targets, and a
  768px touch context. The current Seats browser regression passes 12/12 and
  the dashboard group-core suite passes 6/6.
- The follow-up UI verifier passes 17/17 checks. Seats and Groups are peer local
  tabs; catalog/detail searches, listener heading, and duplicate Simulation
  status are gone. The selected-group Seat filter is case-insensitive prefix
  matching and survives live rerenders while retaining focus and caret.
- No `.pd` file changed. Promoted All/Group/Seat live controls still belong only
  to downstream stitch 12.

## Next implementation session

1. Read `CLAUDE.md`, this handoff, and run `./.loom/loom.sh status`.
2. If Bob requests a checkpoint, commit the tied Seat-group delivery first.
3. Claim
   `ui-tabs/tabs-3-next-sweep/11-assets-device-workflow/11a-device-asset-inventory`.
4. Continue through Assets 11a then 11b; fleet-wide asset rollout remains in
   the separate `asset-fleet-distribution` goal.

## Verification caveats

- The physical iPad, installation projector, LAN/node, audio engine, and
  audible rig were not exercised.
- Two older retained verifiers have stale pre-Seat-model fixtures, recorded in
  `.loom/tied/seat-groups-3-delivery/results.md`; neither reaches a
  Seat-group-delivery assertion.
