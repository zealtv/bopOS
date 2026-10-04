# 2-drop-params-patch-and-revert

**Status:** after `1`
**Goal:** live controls follow the fleet patch; the separate `params_patch`
pointer and the Revert button (`fleet_patch.previous`) are gone.

Spec: `../0-project-design/proposal.md` (ratified 2026-10-04; names and choices in `../0-project-design/rulings.md`).
Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit; leave the system working.

- Remove `params_patch` and its fallbacks (`server.py` live-control manifest
  and declarations, `state.py`, venue load); controls read the fleet patch.
- Remove `revert_fleet_patch`, `previous` bookkeeping and the Revert UI. The
  operator deploys the earlier patch instead (Set Live once `6` lands).
- Strip both fields on load; no compatibility code.
