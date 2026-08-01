# 1-mode-switch-launches-editor — decisions

Implemented in `dashboard/static/js/dashboard.js`, `setExecutionTarget()`.

- Clicking the menu-bar **Patch Edit** target now **launches** the editor
  (`set_edit {active:true, patch, confirmed:true}`) using the same patch the
  in-tab launch button would (`contextualExecutionPatch()`), then switches to
  the Patches tab and focuses the selector. If already in `edit` mode it is a
  no-op except tab/focus.
- **Leaving** edit mode already closed the editor (Live Fleet → `set_edit
  {active:false}`; Simulation from edit → `set_simulation` stops edit
  server-side); confirmed unchanged and covered by the verify.
- **Confirm wording:** from `off`, matches the in-tab launch button verbatim
  (`Open "<patch>" in Patch edit? ...`). From `simulate`, one combined confirm
  (`Stop Simulation and edit "<patch>"?`) then `set_simulation{active:false}` +
  `set_edit{active:true}` back-to-back — no double confirm.

Both enter/exit affordances (menu-bar toggle + in-tab button) kept and verified
in sync (Bob, 2026-07-24).

## Verification
`verify_editor_toggle.py` (in this dir) — Playwright against real
`dashboard/server.py` + `tools/simfleet.py` with `--sim-no-engine` (edit mode
reached headlessly; PD subprocess not needed, matching
`tests/verify_device_control_modes.py`). 15/15 checks + no page errors.
Independently re-run by the orchestrator, not just the delegate.
`~/.venvs/bopos/bin/python verify_editor_toggle.py` (run from repo root).

Implementation delegated to a Sonnet subagent against a full spec; diff judged
and verify re-run by the orchestrator before tie.
