# Show tab polish braindump

Bob's 2026-07-19 feedback pass on the shipped 14-show-tab slice plus three
Patch tab items. Authorizes the `15-show-polish` sweep.

## Source

Bob, 2026-07-19, after operating the completed Show tab (all of
`14-show-tab` tied, including 6b show management) and the Patches manifest
editor. Verbatim text in `content/braindump-2026-07-19.md`.

## Status

Authorized for implementation as laid out on the loom in `15-show-polish`
(ordered stitches, bugs first). Decomposition and sequencing recorded in
`.loom/threads/15-show-polish/instructions.md`; the handoff for the next
session is `.notes/handoff-2026-07-19-show-polish.md`.

Notable rulings inside it:

- Exclusive playback: only one step may play at a time (single column).
- forward_sync per-step flag is retired — all cues forward-sync by design,
  with a global (settable) cue lead time.
- Message clipboard goes keyboard-only + drag-and-drop; the edit-section
  buttons are removed. Keyboard undo is required.
- "facilitator" renames to "Dashboard" on the Patch tab; the legacy
  presentation-only `group` manifest field is removed along with demo
  manifest tidying.
