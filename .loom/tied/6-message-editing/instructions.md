# 6-message-editing

Structural editing: messages move between steps; steps and dividers are
managed in the table. Requires stitches 4–5.

Scope:

- Message operations on pills: copy, cut, paste (into the focused/target
  step), move (drag between steps or explicit move controls — pick what
  fits the existing dashboard interaction idioms and touch layout), delete.
  Clipboard is app-local state; paste clones with a fresh uid.
- Step/divider operations: add step, add divider, delete (with confirm for
  non-empty steps), reorder (move up/down at minimum; drag if cheap).
  Deleting a step referenced by a `goto` follows the design-note edge-case
  rule.
- All edits persist via the stitch-2 surface and broadcast so a second
  client stays consistent.
- Keyboard where natural (copy/paste on focused pill) but buttons must
  exist — touch is first-class.
- Empty-state dead end (Bob's 2026-07-19 screenshot: a fresh show says
  "This show has no steps yet." with no affordance anywhere): the empty
  state must itself offer Add step, not only the populated table.

Verify: `verify_show_editing.py`, Playwright. Cover: copy/cut/paste a
message between steps (uid freshness on paste), delete a message, add/move/
delete steps and dividers with section derivation visibly updating,
persistence across reload, and a goto pointing at a deleted step handled
per the design note.
