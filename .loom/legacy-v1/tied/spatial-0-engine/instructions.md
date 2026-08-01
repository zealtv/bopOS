# spatial-0-engine

Backend spatial automation engine — Stage A of `../instructions.md`, the
computation half (UI is spatial-1).

Design the internals as **mask → per-device value → parameter** from day one
(see `../../scene-sequencing/video-mask/instructions.md` — point+radius+falloff
is just the first mask; video or node-side primitives may slot in later).

- [x] Engine in the dashboard backend: a point (x, y) + radius + falloff curve;
      animatable (programmatic path/LFO now, drag arrives with spatial-1).
- [x] Per-device gain from `installation.json` positions, sent at ~20–30 Hz.
      Contract §4 settles the transport: dashboard-computed per-device
      `/p/gain` is the correct first implementation (fine ≤ ~12 nodes and on
      the audition rig); broadcast `/pt` node-side falloff is Stage B (Bob
      co-design, stays in parent).
- [x] Compose with the existing gain model, don't fight it: facilitator already
      sends stored mix × master on the wire. Spatial multiplies in
      backend-side (stored × master × spatial). Keep manual gain and presets
      untouched — spatial is runtime-only, never persisted. Decide and record
      whether that lives in a shared gain-resolution helper.
- [x] simfleet: nothing new needed if it already logs `/p/gain`; verify it does.
- [x] verify_*.py: animate a path across sim positions, assert per-device gain
      envelopes match falloff(distance) over time.
