# Verification (2026-10-27, main at 6ceaf19 + this change)

`tests/verify_unplaced_tray.py` used a real dashboard on private ports and a
10 × 8 m room with 15 unplaced Seats:

- every Seat's dot sits inside the svg box at 1440 px and 390 px;
- the Seats form three rows, and the tray rect encloses every one;
- dragging Seat 14 from the last row into the room places it, and dropping
  it on the tray's bottom row unplaces it again;
- there's no horizontal scroll at 390 px and no page errors.

Against the old `spatial.js` (stashed), the journey fails: Seats 7–14 fall
outside the map, there's one row, and the drag times out.

`verify_global_controls_monitor.py` and `verify_ground_and_card.py` (the
other journeys that touch the tray) still pass.

Screenshots: `tray-desktop.png`, `tray-390.png`.
