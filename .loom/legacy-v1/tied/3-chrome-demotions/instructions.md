# 3-chrome-demotions

D8, ratified by Bob as a deliberate behaviour change: take three chrome
controls out of the Control column's cards.

Authority is `.loom/tied/1-columns-design/decisions.md` D8. Read the parent
`4-n-columns/instructions.md` first.

Last of the three siblings on purpose. These are changes to the **shared**
`ControlSurface` and to `ControlColumn`'s card, so they land on the Device tab
and the patch editor too — better done once the column count has settled than
while `1` is still moving the layout under them.

## Why

Six chrome controls per seat card × three cards per mixture × three columns is
fifty-four controls before the operator reaches a parameter. At N=1 that
arithmetic did not bite, which is why it survived this long.

## The three

1. **Device commands leave the Control column** — Update bopOS / Reboot /
   Shutdown, rendered by `deviceCommands()` in `js/control-column.js`. **They
   stay on Remote**, so this is a `full`-conditional removal, not a deletion:
   the Devices tab owns device lifecycle, and `07`'s "Set patch…" hand-off is
   the pattern to follow for getting there from a card.
   `css/control-column.css`'s `.control-column .device-commands` block was
   written in `3-iframe-retirement` with a comment naming this stitch as its
   owner — it stays, because Remote still draws it.
2. **`new`/`save`/`del` demote behind one disclosure**, `<select>` stays in the
   row. Note `del` is **patch-scoped** — it removes the preset from the store
   for the whole installation (`control-surface.js`) while sitting in a row
   whose every other control is target-scoped. Worth making that legible while
   moving it, but do not change what it does.
3. **`Send all` moves to an overflow** (`replayButton()` in
   `js/control-column.js`) — a rescue action for a returning node, not a live
   gesture. Confirmed by Bob separately.

## Watch for

- The preset row is `ControlSurface.presetRow`, shared by Control, the Device
  panel and the patch editor. Decide explicitly whether the disclosure is the
  component's new shape everywhere or Control-only, and say which in
  `decisions.md` — a per-host fork here is the pattern this whole thread exists
  to delete, so prefer the component.
- `Send all` is `data-replay-live`, bound in `ControlColumn.bindCards`. It is
  asserted by `verify_control_tab.py`; the assertion moves with the control
  rather than being dropped.
- `.live-card .send-all` in `control-panel.css` §18 is the card's face for it
  and follows it into the overflow.
- Remote keeps all three today. Anything this stitch changes on Remote is a
  measured collapse and belongs in `feature-backlog/49-remote-ipad-restyle`'s
  table, the way `3-iframe-retirement` recorded `Send all`'s 88 × 44 → 54 × 24.

## Verify

`tools/run-tests.sh fast` and `browser`. `verify_control_tab.py`,
`verify_device_control_panel.py` and `verify_preset_control_surface.py` all
assert the current placements — update them where the control moved, and add
the Remote case: `/facilitator` still carries device commands after the Control
column stops rendering them.

Screenshots of a Control column before and after, so the fifty-four-controls
claim is visible rather than asserted.
