# spatial-map — verification

Date: 2026-07-08, dev laptop, loopback (real dashboard + real simfleet,
headless Chromium driving the actual UI).

## What ran

`verify_spatial.py` — 11/11 PASS:
- assigned devices render on the map; devices without positions start in the
  UNPLACED tray
- click selects (same selection as the device list)
- pointer-drag from tray places a device; positions clamp to room bounds
- manual double-click toggles pos2 (speaker pair renders with a connecting
  line) — native dblclick can't work because click-select rebuilds the SVG
  between clicks, so pointerup does its own 400 ms double-click detection
- pos1/pos2 and room bounds persist to `installation.json` (debounced save);
  values are metres, origin top-left, x right, y down
- a second browser sees placements (multi-browser sync)
- dropping a device back on the tray unplaces it (pos cleared)

Screenshots: `01-tray.png`, `02-placed.png`. Also re-ran the tied
os-admin-verbs end-to-end suite after touching state.py/server.py — still
green.

## Not covered (needs a human / real rig)

- Touch dragging on a real iPad (pointer events should cover it; untested)
- Drag feel/ergonomics — Bob may want bigger circles or snap-to-grid
- Real fleet positions from bopos.devices seed rows with POSL/POSR
