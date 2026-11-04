# 2-input-sim-panel

Bob chose option A (`../proposal.md` §4) on 2026-11-04: a simulated keys and
mouse panel in Patch Edit, beside the simulated I2C panels.

## Built 2026-11-04

- When Patch Edit's input source is *simulated*, the Modules tab shows a
  **key · mouse** panel first. It has pads for the Makey Makey defaults (up
  down left right space w a s d f g), a "Type keys" field that captures real
  typing (browser key codes mapped to the bridge's kernel names; Tab still
  leaves the field), left/right click, wheel ↑/↓, and an XY pad (drag, or
  arrow keys with Shift for bigger steps). The last message sent shows under
  the panel.
- Events go one message per press or move via the new websocket message
  `send_editor_input` → `EditorInput.send_input` → one `/io/key` or
  `/io/mouse` packet to the audition engine's 6662. Simulated I2C panels are
  pumped at the poll rate; these aren't.
- `io_protocol.validate_input` is the one validator. Its tests check that it
  accepts every name the bridge can send.
- Held keys and buttons are released on window blur (browser), owner
  disconnect, session end and Performance (server).
- No pop-out for this panel; it lives in the dock only.
- Not covered: a live device source in Patch Edit doesn't carry its real
  keys to the audition engine (keys aren't in the IO stream).

## Verification

- `tests/test_editor_key_input.py` (fast tier): validator, owner-scoped
  release, session-end release, refusal outside a simulated session.
- `tests/verify_editor_input.py` (browser tier) drives the real panel:
  focused pad with Space, typed W and 1, left click, an XY click at 0.25 0.75,
  wheel, release on blur, release on socket loss, the panel gone and sends
  refused in Performance. Passed 2026-11-04 on the laptop (Chromium).
- Screenshots in this folder: `editor-input-{1440,420}-{light,dark}.png`.
  The panel's wording ("key · mouse", "Type keys", "left click", "wheel ↑")
  is operator-visible: Bob to OK it with the screenshots.
