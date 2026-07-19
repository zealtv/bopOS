# show-transport-spot-fixes

Bob's 2026-07-19 Show transport spot fixes, validated against exclusive
playback and the current browser redraw path:

- Remove the redundant global Stop-all button and `0/1 playing` text. Keep the
  single active-step Stop control.
- Left-align the divider drag handle with step drag handles.
- Pausing must leave Resume immediately clickable: paused state must not keep
  the countdown re-render timer alive or replace the button mid-click.
- Make timed-step progress fill smoothly while retaining authoritative server
  playback snapshots and the existing remaining-time display.

Verify in a focused Playwright regression plus the adjacent p2/p3/p4/p6 tied
Show verifiers. Never edit `.pd` files. Retain exact results in `worklog.md`,
tie, commit, and pause.
