# Accepted next sweep after tabs-2

Bob accepted this ordering on 2026-07-15 with one amendment: production points
remain runtime-only and do not persist with venues. The former
`04-venue-point-persistence` stitch is dropped. `01` is the sole loose end;
later stitches remain waiting on their predecessors or design gates.

## Phase A — correctness before IA movement

1. `01-simulation-transition-coherence`: reject late updates for removed virtual
   uids; prove Simulation/Patch edit → Live clears cards and restores target,
   assignment, master and mute without refresh.
2. `02-patch-switch-terminal-state`: bounded switching state, timeout/failure,
   observation-based reconciliation and reliable one-device Retry.
3. `03-seat-identity-leaks`: remove hostname auto-renaming, label Dashboard
   cards from bound seats, and reset selection/detail after bind/unbind/remove.
4. **Dropped:** venue point persistence — Bob confirmed it is not wanted.

## Phase B — ratified execution and noun boundaries

5. `05-global-execution-target`: top-bar Live fleet / Simulation / Patch edit
   control; remove `Edit this patch`; preserve contextual patch selection and
   guarded transitions.
6. `06-seat-device-boundary-design`: short decision record for map-first and
   device-first binding, atomic seat reindex/preset migration, one roster, and
   the UID-targeted admin seam for unbound boxes. Return to Bob for ratification
   if the OSC contract must change.
7. `07-seats-workspace`: move seat create/delete/name/ID/position and binding
   into Seats; keep map-first Identify/Assign.
8. `08-unbound-admin-seam`: implement the ratified unique targeting mechanism
   in node, dashboard, simulator and contract before exposing unsafe controls.
9. `09-devices-workspace`: one roster; full device facts/actions regardless of
   binding; direct Identify, Shutdown All, drift and one-click repair; no seat
   geometry or mix params.

## Phase C — content and live workflow

10. `10-patches-fleet-workflow`: choose/deploy the sole desired fleet patch in
    Patches; Patches owns Set/Revert, Devices owns exception repair.
11. `11-assets-fleet-workflow`: populate Assets with host catalog, fleet
    deployment/sync progress and the same exception pattern.
12. Resume `framework-version-management/version-0-currentness-design` and
    implement its accepted current/update model in Devices.
13. `12-dashboard-live-controls`: all-seat promoted-param controls and review
    preset/cue/card targeting after seat labels land.

## Phase D — diagnostic polish and later identity

14. `13-diagnostic-density`: short fingerprint tails, click-to-copy full values,
    target counts and action feedback.
15. `14-device-alias-design`: deterministic curated human alias + editable
    registry design; keep hostname/uid as technical secondary identity.

After this sweep, resume `patch-workflow-friction` so documentation describes
the stable production workflow rather than the transitional skeleton.
