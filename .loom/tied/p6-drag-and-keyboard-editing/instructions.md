# p6-drag-and-keyboard-editing

The editing-model rework. Biggest stitch in the thread — split if it
fights back (drag vs undo are natural halves).

1. **Message rearranging by click-and-drag**, within a step and between
   steps (existing `move_message` WS op is the backend). Drag affordance
   on the pill; drop targets between pills and on other steps' pill rows.
   Touch is first-class (the dashboard is operated on tablets) — pointer
   events, not HTML5 drag-and-drop, if that's what it takes; log the
   choice. Keep the Playwright drag gotchas from CLAUDE.md in mind
   (scroll position, clamped coordinates).
2. **Steps and dividers reorder by click-and-drag** (backend: `move_item`).
   Same pointer-event machinery; a drag handle or whole-row long-press —
   pick what coexists with row click-to-focus and transport buttons, and
   log the reasoning.
3. **Edit-section buttons go.** Cut/copy/move (left/right/other-step)
   buttons are removed from the inspector edit section. Cut/copy/paste and
   delete stay keyboard-only on the focused pill (existing bindings; keep
   them working); delete-by-keyboard confirmed good. Buttons that remain:
   paste needs a decision — keyboard-only paste is fine per the braindump
   ("cut and copying ... can be keyboard only"); if an on-screen paste
   affordance is retained anywhere, justify it in the worklog.
4. **Keyboard undo.** Ctrl/Cmd+Z undoes show edits (structural and
   message edits at minimum; step/message field edits if cheap). The WS
   surface is full-state broadcast, so the cheap correct shape is a
   client-local stack of show snapshots with an `apply_show` full-document
   WS op — or a server-side history; pick one, design it in the worklog
   before coding, keep last-writer-wins semantics for second clients
   sane (undo applies as a normal edit broadcast). Redo optional; note if
   deferred.

Verify: `verify_show_drag_editing.py` (house pattern): drag a pill within
a step (order persists), between steps (parent changes), drag a step
above another (order persists after reload), keyboard cut/paste still
moves a message, keyboard delete removes, Ctrl+Z restores the deleted
message, removed buttons absent from the DOM. Re-run tied 6's editing
verify and amend for the removed buttons (log it).
