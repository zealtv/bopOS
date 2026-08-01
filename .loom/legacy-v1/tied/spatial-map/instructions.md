# spatial-map

**Split 2026-07-08 from the parent:** the spatial map is operator tooling from
the ratified dashboard design (`.notes/dashboard-development-context.md` §9)
and the authoring surface `spatial-audio` will build on — buildable now. The
facilitator view is Bob's decision gate and lives in the sibling stitch.

Checklist:
- [ ] SVG top-down spatial map in the technical dashboard: devices as
      draggable circles; colour = online status; click to select (same
      selection as the device list)
- [ ] Drag-to-position writes pos into `installation.json` via a
      `set_position` ws message; broadcast to all browsers
- [ ] **Coordinate system explicit**: units (metres), origin, and room bounds
      stored in `installation.json` (e.g. `"room": {"width": 10, "depth": 8}`)
      — spatial-audio will consume these
- [ ] Devices with two speaker positions (pos1/pos2) render both points
      (speaker pair), draggable independently
- [ ] Unpositioned-but-assigned devices parked in a tray at the map edge,
      draggable onto the map

Notes:
- Positions already ride `/os/assign` (args 3-7) and simfleet persists them;
  no wire change needed — this is dashboard-side state + UI only.
- Keep it vanilla SVG per the design doc; no libraries.
