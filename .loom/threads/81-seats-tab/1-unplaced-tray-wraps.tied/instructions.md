# 1-unplaced-tray-wraps

Bob, 2026-10-27: "unassigned seats currently overflow their container and
become unviewable. the container should resize." (He means the Seats map's
UNPLACED tray: Seats with no position.)

## What the code does (read 2026-10-27, `dashboard/static/js/spatial.js`)

- `TRAY_H = 1.2` m is a constant. The tray rect spans the room width `W`
  (line ~79), and the viewBox height adds a fixed `TRAY_GAP + TRAY_H` (~66).
- Each unplaced Seat gets `[0.7 + 1.7 * slot++, D + TRAY_GAP + TRAY_H * 0.62]`
  (~117): a single row at 1.7 m spacing that never wraps. In a 10 m room,
  everything past the 6th unplaced Seat lands outside the tray and the
  viewBox, so the operator can't see it or drag it.

## Do

- Lay unplaced Seats out in rows that wrap at the room width, keeping the
  spacing, and size the tray (and the viewBox) to the number of rows. One
  row of Seats should look the same as it does today.
- Drop-to-unplace uses `y > D + TRAY_GAP / 2` (~465, ~508), which still
  holds for a taller tray. Check that dragging a Seat out of a lower row
  into the room places it, and that dropping it anywhere in the tray
  unplaces it.
- The map's CSS height (`.seats-tab #spatial` `min(68vh,720px)`, 50vh on a
  phone) stays fixed, so a deep tray shrinks the room drawing. Decide
  whether that's acceptable at ~20 unplaced Seats in a small room, or
  whether the svg should grow instead. Record the decision in the stitch
  directory.
- Seat dots are drawn at a fixed size in metres (`ELEMENT_R = 0.2`), so a
  very small room crowds them. Spacing may need to scale with `W`. Note what
  you chose.

## Verify

A Playwright journey on private ports (see glean `playwright-gotchas`;
`tests/verify_device_roster_sort.py` shows the `--input-port` and
`--stream-port` pattern). Use a fixture with a 10 m room and ~15 unplaced
Seats, and check:

- every unplaced Seat's bounding box sits inside the svg's box;
- dragging one from the last row into the room places it;
- desktop width and 390 px width both work.

Include a screenshot for Bob.
