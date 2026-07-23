# 2-edit-session-button-cleanup — decisions

Implemented in `dashboard/static/js/dashboard.js`, `renderEditor()`.

- **Removed:** "Hear it in the sim" (`#editor-hear-sim`), "Restart"
  (`#editor-restart`), and the "Launch selected patch" active-state label on
  `#editor-launch`. Their click handlers were removed too.
- **`#editor-launch` toggles in place:** "Launch editor" when off, **"Stop
  Editor"** when the editor is active; the Stop Editor click carries the old
  Stop confirm + `set_edit {active:false, confirmed:true}`. It stays enabled
  while active so Stop is always reachable.
- **`#editor-session-actions`** now renders only the **Relaunch** button, and
  only in the engine-closed case; empty otherwise. `#editor-relaunch` kept and
  functional.
- `index.html` needed **no change** — the button markup was already generic;
  the label/behaviour is JS-driven.

The retired separate `#editor-stop` role moved onto `#editor-launch`; both
enter/exit affordances kept in sync per Bob (2026-07-24).

## Verification
Shared with `../1-mode-switch-launches-editor/verify_editor_toggle.py` (the one
Playwright run covers both stitches). Asserts the removed buttons never render
in off / active-alive / active-closed states, and the Launch editor ⇄ Stop
Editor relabel. 15/15 + no page errors; re-run by the orchestrator.
