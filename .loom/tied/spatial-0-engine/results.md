# spatial-0-engine — results

Stage-A spatial automation engine, dashboard-computed. Point (x, y) + radius +
falloff → per-device `/p/gain` at ~25 Hz, composed as **stored × master ×
spatial**, runtime-only (never persisted). Contract §4 already ratifies
dashboard-computed per-device `/p/gain` as the correct first implementation, so
no contract change and no decision gate here (Stage B `/pt` node-side falloff
stays in the parent, Bob co-design).

## What landed

- **`dashboard/spatial.py`** (new, pure math, no OSC/state deps): falloff curves
  (`linear`, `smooth` smoothstep, `gauss`), motion kinds (`static`, `path`
  polyline sweep, `orbit` circular LFO), `device_factor(config, pos, elapsed)`,
  `is_dynamic`, and `sanitize`/`default_config` for untrusted ws payloads.
  Designed **mask → per-device value** from day one (`device_factor` is the seam
  a video/node-side mask slots into later — see scene-sequencing/video-mask).
- **`dashboard/osc_bridge.py`**: `send_device_param` now folds the spatial
  factor into the volume param alongside master (see decision below); added
  `_spatial_factor`, `set_spatial`, the `spatial_loop` tick task (change-gated,
  only ticks while a point is *moving*), and `_spatial_tick`.
- **`dashboard/state.py`**: seeds `data["spatial"]` inactive at room centre;
  runtime-only — `durable()` builds an explicit key set that excludes it, so it
  is never written to `installation.json` or a venue.
- **`dashboard/server.py`**: `set_spatial` ws command — full-state/idempotent
  (contract §4), sanitizes the payload, applies via the bridge, broadcasts
  `spatial`. This is the surface spatial-1's drag/path UI drives.
- **`tools/simfleet.py`**: logs applied patch-plane values (`p/<name>=<v>`) so
  spatial/gain automation is observable off the wire (the stitch's "verify
  simfleet logs `/p/gain`" — it did not; now it does).

## Decision — shared gain-resolution helper (asked by the brief)

**Yes, but the helper already existed.** `send_device_param` was already the one
place that resolved a device's wire volume (stored mix × master). Spatial is a
third multiplicand, so it multiplies **in the same method** rather than in a new
helper or a parallel `/sgain` path. Every emitter of a volume — manual set,
preset load, master move, spatial tick — routes through `send_device_param`, so
the three factors compose in exactly one place and can't drift. Unpositioned
devices and devices with no volume param resolve to factor 1.0 (untouched),
never silenced.

## Verify

`verify_spatial_engine.py` — real `server.py` + `simfleet` on non-default ports,
browser-free (the engine is server-side; output is the `/p/gain` on the wire,
read back from simfleet's log). Assigns 3 sim devices to a known floor line,
drives the layer over `/ws` as spatial-1's UI will.

Command (deps: `pip install fastapi uvicorn[standard] python-osc websockets`):

    python3 verify_spatial_engine.py

Result: **18/18 PASS**. Covers static exactness (applied gain == falloff(distance)
to ±0.01 across a 3-point sweep), master composition (0.5 halves the applied
gain), dynamic envelope (each device rises to ~1.0 then falls; peaks arrive in
spatial order a<b<c), restore-on-deactivate (back to stored × master), and a
set_param regression + no server traceback. Regression: tied
`sync-1-leader/verify_sync_leader.py` still 10/10 PASS (send_device_param and
`state.public()` changes don't disturb the sync plane).

## Not done here (by design)

- **UI** is spatial-1 (drag/path authoring on the spatial map). The engine
  already accepts `static`/`path`/`orbit`; the UI mostly sends `static` points.
- **Stage B** (`/pt` broadcast, node-side falloff for 50–100 nodes) stays gated
  in the parent thread — Bob co-design.
- **Hardware/audible sweep** (parent's Stage-A "done when") needs the audition
  rig or a real fleet; the software floor is verified.
