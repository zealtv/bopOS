# 1-mode-switch-launches-editor

Make the menu-bar mode switch drive the editor lifecycle (Bob, 2026-07-24).

- Clicking **Patch Edit** in the execution-target switch
  (`dashboard/static/index.html:6`, `data-execution-target="edit"`) should
  **launch the editor** — i.e. enter edit for the currently selected/effective
  editor patch — rather than merely arm the mode and wait for a separate
  "Launch editor" press.
- Switching to a **different mode** (Live Fleet / Simulation) should **close
  the editor** (`set_edit {active:false}`), respecting the existing
  confirmation flow when leaving a running edit session
  (see `set_edit` / `set_simulation` handling, `dashboard/server.py:728`+, and
  the client mode-switch confirms `dashboard/static/js/dashboard.js:501`).

Reconcile with `38-patch-edit-chrome/2` — once Patch Edit launches the editor,
the separate "Launch editor" button is being retired there; keep the patch
**selector** so an operator can choose which patch before/while editing.

Which patch launches when Patch Edit is clicked (last selected `editorPatchChoice`
vs the fleet patch fallback, `dashboard.js:706`) — pick the least-surprising
default and note it in `decisions.md`.

Simulator parity + Playwright coverage for: click Patch Edit → editor active;
switch away → editor closed (with confirm).
