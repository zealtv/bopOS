# 1-remove-device-pins

**Status:** ready · pure deletion
**Goal:** every box in the fleet runs the fleet patch; per-device patch pins are gone.

Spec: `../0-project-design/proposal.md` (ratified 2026-10-04; names and choices in `../0-project-design/rulings.md`).
Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit; leave the system working.

## Delete (proposal §3)

- `set_device_patch` / `clear_device_patch` actions, `device_operations`,
  `device_generations`, `converge_device_patch` (`dashboard/server.py`).
- `desired_patch` in the device registry (`dashboard/state.py`,
  `dashboard/device_aliases.py`) — strip it on load, no compatibility layer.
- The `patch_pinned` projection; `device_patch_for` and the per-device manifest
  lookup in `live_control_manifest` / control declarations.
- Pin UI in `dashboard/static/js/dashboard.js` ("Pin to device", "Follow fleet
  patch", 📌, `.patch-pin` CSS) and the Patches-tab per-device target picker
  (`#patch-target`): deploy is whole-fleet only.
- Tests: `tests/test_device_patch_override.py`,
  `tests/verify_device_patch_targeting.py` (keep any whole-fleet checks worth
  having by moving them), the pin part of `tests/verify_set_patch_handoff.py`.

## Verify

Fast suite green; a browser journey deploys whole-fleet; `rg -i "pin"` over
dashboard code shows no pin machinery left. `69-complexity` relies on this list.
