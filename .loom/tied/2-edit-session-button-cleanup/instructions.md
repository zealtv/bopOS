# 2-edit-session-button-cleanup

Trim and relabel the Patch Edit session controls (Bob, 2026-07-24). All in the
`renderEditor()` block, `dashboard/static/js/dashboard.js:701`.

Remove:
- **"Hear it in the sim"** (`#editor-hear-sim`, dashboard.js:749/752).
- **"Restart"** (`#editor-restart`, dashboard.js:749/751).
- **"Launch selected patch"** — the `#editor-launch` label when the editor is
  already active (dashboard.js:728). Its purpose is unclear; retire that
  active-state action. (Selecting a patch is done via the `#editor-patch`
  selector; keep the selector.)

Rename / swap:
- The **Stop** button (`#editor-stop`, dashboard.js:749/757) becomes
  **"Stop Editor"**.
- On entering Patch Edit, **"Stop Editor" replaces the "Launch editor" button**
  (`#editor-launch`, `index.html:83`) — i.e. one button in that spot: "Launch
  editor" when off, "Stop Editor" when editing.

**Decided (Bob, 2026-07-24): keep both affordances for now** — the menu-bar
Patch Edit toggle (`38/1`) *and* this in-tab Launch editor / Stop Editor
button. They must stay in sync (flip either, both reflect the edit state).

Keep the confirm on stop ("Stop Patch edit and return audio control to the Live
fleet?"). Consider whether `#editor-relaunch` (engine-closed case, dashboard.js:750)
still has a role once Restart is gone — note the call in `decisions.md`.

Update the affected Playwright verifies (they assert the old button set/labels).
