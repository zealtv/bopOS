# ui-2 results

The listener's heading tip is now a drag-dial, distinct from dragging the puck
body to move the listener. The numeric heading input is gone, leaving a compact
live readout.

Device/element dots keep a constant radius and opacity. Authored points instead
carry a stable colour across their list item, handle, and dashed falloff field.
Point fields and handles share an SVG room clip. The list provides a reliable
selection target for moving points.

The position jump came from rebuilding bounce motion at stale `point.x/y`
coordinates. Radius, falloff, motion, and velocity edits now rebase at the
currently displayed position before restarting the edited trajectory. The
maximum continuity adjustment is the dashboard's two-decimal coordinate
rounding (< 0.01 m).

## Verification

- PASS: `node --check dashboard/static/js/spatial.js`
- PASS: `node --check dashboard/static/js/dashboard.js`
- PASS: `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile .loom/threads/dashboard/dashboard-9-ui-review/ui-2-spatial-map-pass.stitching/verify_ui2_spatial.py`
- PASS 9/9: `~/.venvs/bopos/bin/python .loom/threads/dashboard/dashboard-9-ui-review/ui-2-spatial-map-pass.stitching/verify_ui2_spatial.py`
- PASS: visual inspection of `ui2-spatial.png` at 1400×1000; point identity is coherent across list/handle/field, clipping is clean, and the heading handle reads as a separate control.
- PARTIAL 6/6 low-level checks, then SETUP FAILURE: `.loom/tied/seam-3-points-node-side/verify_points_node_side.py` passes true-N assignment, persistence, decomposition, sparse upsert, clear, and empty-frame release. Its later dashboard-stack phase stops before assertions because no simulator row with ID 1 appears, the same stale setup condition seen in other tied harnesses this session.

Listener visibility remains unchanged and awaits `d8-2-simulate-toggle` as
required. Not verified on iPad/touch or installation hardware.
