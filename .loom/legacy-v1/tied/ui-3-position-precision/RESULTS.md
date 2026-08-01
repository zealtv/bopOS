# ui-3 results

Selected assigned devices now expose one numeric x/y row per positioned
element, labelled from element 0. Changing a coordinate sends `set_position`,
the same dashboard path as map dragging; the server consequently emits the
ordinary complete `/os/assign` and the node persists the true-N list.

The room now persists `origin: [x, y]`, a visual coordinate datum constrained
inside its width/depth. The marker is where relative `(0,0)` lies. Numeric
fields display `local position - origin`; typed values are converted back to
the existing local room coordinates before assignment. Moving the origin thus
aligns/re-labels the plan without silently moving devices, points, listener, or
changing the established wire coordinate model.

## Verification

- PASS: `node --check dashboard/static/js/dashboard.js`
- PASS: `node --check dashboard/static/js/spatial.js`
- PASS: `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/state.py .loom/threads/dashboard/dashboard-9-ui-review/ui-3-position-precision.stitching/verify_ui3_positions.py`
- PASS: direct `InstallationState.clean_room` checks for default and explicit origins.
- PASS 9/9: `~/.venvs/bopos/bin/python .loom/threads/dashboard/dashboard-9-ui-review/ui-3-position-precision.stitching/verify_ui3_positions.py`
- PASS: visual inspection of `ui3-positions.png` at 1400×1000; the datum is clear, true-N rows are compact, and the origin controls remain subordinate to the map.

The verifier uses the real dashboard and simfleet. It proves two element rows,
0-indexed labels, relative display, node-side persistence of the complete
assignment, marker movement, installation persistence, and re-label without
movement. Not verified on iPad/touch or installation hardware.
