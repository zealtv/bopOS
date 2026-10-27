# Decisions (2026-10-27)

- **One toggle for the map and the list.** A "Device names" checkbox in the
  map toolbar (next to Add point) labels each Seat on the map and adds the
  device's name to its row in the Seat list ("ID 1 · live · Abel Fern").
  Neither surface named the device before, so one switch covers both.
- **Off by default**, remembered per viewer in localStorage as
  `bopos.seat-device-names`, inside try/catch. The state lives in
  `spatial.js` (`Spatial.deviceNames`) because the map owns the drawing.
- **Label placement:** centred under the first element's dot, so a paired
  Seat gets one label. It carries a halo in the canvas colour (paint-order
  stroke) so it reads over rails and fields in both themes. It never takes
  the pointer. Names longer than 16 characters get an ellipsis; the full
  name stays in the tooltip.
- **Unbound Seats show nothing.** A dim "unbound" on every empty Seat would
  clutter a map that's mostly placement; the dot colour and the list row
  already say empty.
- **Simulation:** a virtual device is named the same way (`Identity.primary`).
- **The tooltip and aria-label always name the device**, whether or not the
  toggle is on.
- **No flicker:** labels are plain text redrawn with the map on each
  heartbeat, with no animation to restart.
