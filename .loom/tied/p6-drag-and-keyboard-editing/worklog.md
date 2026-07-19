# p6 drag and keyboard editing — worklog

## Design decisions (before implementation)

- **Messages:** the pill itself is the drag affordance. Pointer movement must
  cross a small threshold before drag starts, preserving ordinary tap/click to
  focus. Drop position is calculated between the other pills in the row; an
  empty step row is also a valid target.
- **Steps/dividers:** use an explicit handle. Whole-row dragging conflicts with
  focus and the transport controls, while a visible handle is unambiguous on
  mouse and touch. The same pointer-event machinery drives both item kinds.
- **Touch:** use Pointer Events with capture, `touch-action: none` on affordances,
  and bounded auto-scroll near the step-list edges. HTML drag-and-drop is not
  used because its touch behavior is inconsistent.
- **Undo:** keep one bounded server-side history for the currently loaded show.
  Every successful persisted model mutation pushes the previous authoritative
  document; Ctrl/Cmd+Z asks the server to restore and broadcast the latest
  entry. This makes undo a normal global last-writer-wins edit for every client,
  avoiding stale client snapshots overwriting a second operator's newer work.
  Loading/switching a show clears history. Redo is deferred.
- **Buttons:** message copy/cut/move/delete and the on-screen paste affordance
  are removed. Copy, cut, paste, and delete remain keyboard operations on the
  focused pill/row. Structural add/delete buttons remain in the step/divider
  inspector; reordering moves exclusively to drag.

## Verification record

- `node --check dashboard/static/js/show.js` — pass.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m
  py_compile dashboard/server.py verify_show_drag_editing.py` — pass.
- `git diff --check` — pass.
- `verify_show_drag_editing.py` — 11 checks, 0 failures: within-step and
  cross-step pill drag, step and divider drag, removed buttons, keyboard
  cut/paste/delete, two-client global undo, reload persistence, no page errors.
- `.loom/tied/6-message-editing/verify_show_editing.py` — 16 checks, 0
  failures after the expected keyboard/button amendment.
- `.loom/tied/p5-inspector-defaults/verify_show_inspector_defaults.py` — 19
  checks, 0 failures after its paste action moved to the keyboard path.
- `.loom/tied/2-model-and-persistence/verify_show_model.py` — all model and
  real server/WebSocket persistence/restart checks passed.
- `.loom/tied/p4-step-list-scrollbox/verify_show_scrollbox.py` — 12 checks,
  0 failures, including touch viewport, resize handle, scroll preservation,
  and horizontal overflow.
- Visual taste pass: `drag-editing.png`; handles remain subordinate to
  transport and aliases, pills retain compact colour identity, and the
  inspector loses the obsolete edit-button block.

All browser tests used temporary loopback ports and headless Chromium. No
physical iPad, hardware fleet, audio, or Pure Data behavior changed or was
required for this Show-authoring stitch.

## Tied verifier amendments

- `6-message-editing`: button-driven copy/cut/paste/delete expectations now use
  the retained keyboard bindings; obsolete move-button checks were removed.
  The focused p6 verifier owns pointer drag coverage.
- `p5-inspector-defaults`: its pasted-message disclosure check now copies and
  pastes with Ctrl+C/Ctrl+V because the p6 on-screen paste button is retired.
