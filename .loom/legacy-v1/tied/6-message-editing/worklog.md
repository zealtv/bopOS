# 6-message-editing worklog — 2026-07-18

Frontend-only structural editing (the backend ops — add_message-as-paste,
move_message, move_item, remove_item, remove_message — were already tied and
verified in stitch 2).

## What changed (`static/js/show.js`, `static/css/style.css`)

- **Clipboard** is app-local (`clipboard` variable): Copy stores
  alias/address/args/target *without* the uid; Paste sends `add_message`, so
  the server mints a fresh uid, and the existing `pendingMessageAdd`
  mechanism focuses the new pill. Cut = Copy + `remove_message`.
- **Message inspector** grew an Edit section: Copy / Cut / Move left / Move
  right (reorder within the step via `move_message` with a computed
  `after_uid`) / Delete, plus a "move to step" select that relocates the
  message (uid preserved — distinct from cut/paste, which clones). A select
  is fine *here*: it's a command, not the target model 5c redesigned.
- **Step inspector and a new Divider inspector** grew an Arrange section:
  Move up / Move down (`move_item`), Step below / Divider below
  (`add_step`/`add_divider` after the focused item), Paste message
  (steps only; disabled while the clipboard is empty), Delete (confirm()
  only when a step still holds messages). Dividers are now focusable rows
  (click/Enter, `focused` outline) so they can be arranged and deleted.
- **Add bar** under the table: `+ Step` / `+ Divider` append at the end.
- **Keyboard** on the focused pill/row: Ctrl/Cmd+C copy, Ctrl/Cmd+X cut,
  Ctrl/Cmd+V paste (into the pill's or row's step), Delete/Backspace
  deletes (same confirm flow); ignored inside form controls. To make this
  work, `render()` now restores DOM focus to the focus-model element after
  innerHTML replacement — only when no form control holds focus.
- **Stale goto surfacing:** a goto whose target step no longer exists
  renders a selected "missing step · uid" option (references are left
  as-is per the design note), and the engine's one-cycle `goto_missing`
  playback flag now renders as a `goto?` badge on the row.

## Verify

- `verify_show_editing.py` (this dir), 17 checks, **0 failures**: paste
  disabled on empty clipboard; copy/paste clones across steps with a fresh
  uid and focuses the clone; cut+paste moves content with a fresh uid;
  keyboard copy/paste; message delete; move-to-step keeps the uid;
  move-left reorders pills; add-bar append; divider-below; item move
  up/down round-trip; divider + empty-step delete need no confirm;
  non-empty step delete raises the confirm dialog; stale goto shows the
  missing-step option; playing a step whose goto target was deleted falls
  back to stopped with the `goto?` badge; the edited structure survives
  reload; no page errors.
  (Playwright note: `wait_for_function` takes its argument as `arg=`,
  not positionally.)
- Re-ran tied 4-tab-ui, 5-inspector, 5b-compact-rows,
  5c-target-model-and-picker: 0 failures each, no amendments needed.
