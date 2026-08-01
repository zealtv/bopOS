# 26-listener-range-fixes

Bob reviewed the tied `22-listener-range-ux` work live on the Seats tab
(2026-07-21, screenshot attached to the request) and found four defects. Three
are rendering bugs in the range field; the fourth retires the Listener toolbar
entirely.

**Bob, 2026-07-21:** "seat tab — listener range radius not clipping to room,
gradient only displayed in right hand quadrant, radius indication not moving
when dragging listener, remove the listener tool bar — not required, all
control can be graphical."

## What Bob saw

With simulation active, room 10 × 8, listener near centre, range 5.73 m:

1. **Range not clipped to the room.** The dashed out-of-room arc sweeps well
   outside the room rectangle, over the UNPLACED tray and off the panel edge,
   and a solid arc reappears at bottom-right outside the room. The tied design
   deliberately drew an out-of-room dashed arc so the true circle stayed
   legible (`.listener-ring-outside`, `spatial.js:159`); Bob's ruling now
   **supersedes that** — the range indication must clip to the room. Record the
   supersession in `decisions.md`, and repair rather than delete any tied guard
   that pins the old behaviour (see CLAUDE.md, "Re-running a tied guard").
2. **Gradient only fills one quadrant.** `.listener-field` fills with
   `url(#listener-field-gradient)` (`style.css:156`), a `radialGradient` with
   three stops (`spatial.js:148-151`) and no `gradientUnits`/`cx`/`cy`/`r`.
   On screen the wash appears only down-and-right of the puck, squared off at
   the listener's x and y — it reads like the gradient's object bounding box
   is being resolved against something other than the translated circle.
   Suspect the `objectBoundingBox` default interacting with the `transform` on
   the wrapping `<g>` and/or the room clip; `gradientUnits="userSpaceOnUse"`
   with explicit `cx`/`cy`/`r` is the likely fix. Diagnose before changing.
3. **Range indication does not follow the listener during a drag.** The drag
   handler moves only the puck group (`spatial.js:415` sets the transform on
   `listenerDrag.group`); the `.listener-range-field` wrapper carries its own
   `transform` set once at render (`spatial.js:155`) and is never updated, so
   the field/ring stay behind until the drag ends and a re-render lands. The
   heading tick lives inside the puck and does follow — the mismatch is
   visible mid-drag.
4. **Retire the Listener toolbar.** `#listener-bar` (`index.html:39-43`:
   range number field, heading number field, readout) goes. All control is
   graphical: tip drag for heading, collar/wheel/keys for range, which
   `22-listener-range-ux` already delivered. See stitch `02`.

## Shape of the work

1. `01-range-field-rendering-fixes` — defects 1–3.
2. `02-retire-listener-toolbar` — defect 4, after `01` (the toolbar readout is
   still a useful diagnostic while fixing the rendering, and `paintRange()`
   writes to it).

No design gate: Bob has ruled on all four. Both stitches ship the usual
Playwright verify (CLAUDE.md, "Dashboard browser tests") plus a before/after
screenshot in the stitch directory.
