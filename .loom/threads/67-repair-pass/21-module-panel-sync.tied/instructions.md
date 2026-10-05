# 21-module-panel-sync

**Status:** ready
**Goal:** module panels (59/9, 59/6) stay consistent through reconnects and
late inventory.

Evidence: `lore:2026-10-05-bopos-review-frontend` F2, F3.

- **F2.** Disconnect nulls `values` but leaves `ready` true; after reconnect a
  simulated slider is enabled and moving it throws (`values` is null). Reset
  readiness on disconnect; keep drive/release inert until fresh session data.
- **F3.** `syncEditor`'s change signature omits the selected device's module
  inventory, so modules reported after picking a device never get panels.
  Include module identity/type in the reconciliation.

Done when: regressions fail before and pass after; `verify_module_panels.py`
and `verify_editor_input.py` green.
