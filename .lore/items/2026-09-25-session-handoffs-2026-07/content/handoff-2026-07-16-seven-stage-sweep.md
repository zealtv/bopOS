# Handoff — seven-stage implementation sweep (2026-07-16)

This supersedes `.notes/handoff-2026-07-15-clean-next-sweep.md` as the current
launch note. The older handoff remains a historical record of the Seats →
Devices transition; Devices and Patches are now tied.

## Current state

- The worktree was clean at `e01e718` before this session's note reconciliation
  and implementation work.
- Loom now has 117 tied stitches, 13 dropped stitches, no claim, and two loose
  ends: Seat-group core and Assets 11a.
- Dashboard next-sweep work is complete through Devices and Patches. Assets is
  still empty; no 11a implementation has begun.
- The nested parameter-address foundation is implemented, verified, and tied.
  The Seat-group protocol/data model and complete spatial UX are ratified; the
  UX proposal and hierarchy review are tied.
- The sequencer notes are a brainstorm only. `scene-sequencing` remains paused
  for co-design and is outside this implementation sweep.

## Start the next implementation session here

1. Read `CLAUDE.md`, this handoff, and run `./.loom/loom.sh status`.
2. Claim `seat-groups/seat-groups-3-delivery/seat-groups-1-core-implementation`.
3. Split it at concrete seams if needed, then implement protocol, persistence,
   matching, simulator/audition parity, dashboard state, and synchronization.
4. Reuse the tied variable-length parameter relay. Do not build group authoring,
   spatial visualization, or promoted live controls in the core stitch.

## Accepted seven-stage sweep

1. **Complete — Parameter-address foundation:** contract/model/relay and
   dashboard state/editor are tied.
2. **Complete — Seat-group spatial UX gate:** the complete interaction and
   hierarchy are ratified and tied.
3. **Next — Seat-group core:** implement the non-visual foundation, reusing the
   variable-length nested parameter relay.
4. **Seat-group delivery:** implement group authoring and the ratified map
   visualization.
5. **Assets:** implement 11a device inventory, then 11b single-device asset
   management.
6. **Dashboard live controls:** integrate the flat/nested parameter ×
   All/Group/Seat matrix exactly once in stitch 12.
7. **Finish and document:** diagnostic density, device-alias design gate, then
   patch-workflow-friction docs and starter kit.

## Boundary reminders

- Work one stitch at a time using claim → work → verify → tie.
- Never edit `.pd`; record concrete nested-route work for Bob in
  `.notes/pd-edits-for-bob.md`.
- Assets manages exactly one online assigned physical device in this sweep.
  Fleet asset rollout remains deferred to `asset-fleet-distribution`.
- Do not create a second live-control implementation in the parameter or
  Seat-group threads. Stitch 12 owns that surface.
- Do not treat the sequencer brainstorm as ratification.

## Primary sources

- `.loom/tied/parameter-addresses/`
- `.loom/tied/param-address-1-implementation/`
- `.loom/tied/seat-groups-2-spatial-membership-ux-design/proposal.md`
- `.loom/tied/param-address-0-design/proposal.md`
- `.loom/tied/seat-groups-0-design/proposal.md`
- `.loom/threads/seat-groups/seat-groups-3-delivery/`
- `.loom/threads/ui-tabs/tabs-3-next-sweep/11-assets-device-workflow/`
- `.loom/threads/ui-tabs/tabs-3-next-sweep/12-dashboard-live-controls.waiting/`
