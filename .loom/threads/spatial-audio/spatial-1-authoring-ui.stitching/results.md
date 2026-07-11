# spatial-1 results

Built the point-set authoring surface on the existing dashboard map:

- arbitrary numbered points with drag streaming, radius ring, falloff picker,
  on/off draft retention, and delete;
- the first programmed mover is a two-axis wall bounce with independent x/y
  velocity; backend triangle-wave reflection keeps the point inside current
  room bounds and active bounces adopt room resizes;
- the server evaluates motion once and sends both the real `/pt` frame and its
  browser display position from the same clock;
- per-element proximity is mirrored only for display (size/brightness), never
  sent as a dashboard-computed gain;
- element index determines colour and each element is numbered with its device
  ID, per Bob's direction;
- the facilitator surface is unchanged.

## Verification

`verify_spatial_authoring.py` — **15/15 pass** against the real dashboard,
simfleet, WebSocket surface, OSC point plane, and headless Chromium:

- bounce sanitizer and deterministic x/y reflection;
- one device group with true element children;
- element colour/index and device-number labels;
- add/edit/drag radius and falloff controls;
- display-only falloff redistribution;
- substantial movement on both axes and positive/negative direction changes
  on both axes (actual wall reflections);
- resized room walls adopted by an active bounce;
- off/on draft behavior and delete;
- simfleet observes changing node-side proximity and release-to-zero.

`node --check` passed for both touched JS files. `python -m py_compile` passed
for the touched Python modules. The tied seam-3 real-helper integration remains
**18/18 pass**, including ~25 Hz movement, true-N/0-based decomposition,
falloff equality, catch-up, sparse edits, and clear release. `git diff --check`
passes.

## Not verified

No audible rig judgment was made. The display math is a legibility aid; node
math remains authoritative. Points remain runtime installation state as before
this stitch, not durable venue state. No `.pd` or facilitator file was edited.
