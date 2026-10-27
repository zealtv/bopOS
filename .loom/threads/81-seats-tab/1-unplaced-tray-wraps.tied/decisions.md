# Decisions (2026-10-27)

- **Layout:** the first row is unchanged: x = 0.7 m + 1.7 m × column. The
  row holds as many Seats as fit between 0.7 m margins (6 in a 10 m room,
  1 minimum). Each further row adds 0.9 m to the tray, which starts at its
  old 1.2 m height. One row looks exactly as it did before.
- **Map height stays fixed.** The svg keeps its CSS height (`min(68vh,720px)`,
  50vh on a phone); a deeper tray makes the viewBox taller, so the whole
  drawing scales down to fit. Fifteen Seats in a 10 × 8 m room take three
  rows (2.7 m of tray), which still leaves the room readable (see
  `tray-desktop.png`). Growing the svg instead would push the sidebar layout
  around; revisit if a fleet of ~40 unplaced Seats makes the room too small.
- **Spacing doesn't scale with the room.** Dots stay 0.2 m in radius at
  1.7 m spacing. A room narrower than 1.4 m gets one Seat per row, so
  nothing overlaps; the tray just runs deep.
- Drop-to-unplace still tests `y > D + TRAY_GAP / 2`, so a drop anywhere in
  the taller tray unplaces the Seat. The journey checks this on the bottom
  row.
