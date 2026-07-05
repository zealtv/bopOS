# spatial-audio

**Goal:** spatialise sound across the device fleet the way belief did on Happy Brackets:
start a sound simultaneously on all devices (synced clock), then move a point through the
space; each device's gain = falloff(distance from point, radius).

Design: `.notes/architecture-review-2026-07-05.md` §6.

Depends on: `clock-sync` (synchronised start) and `dashboard-2-spatial-facilitator`
(positions + authoring surface). Sequenced here by instruction, not nesting — check those
before starting.

Stage A — dashboard-computed (do this first):
- [ ] Spatial automation layer in the dashboard backend: a point (x, y) + radius +
      falloff curve, animated by drag/path/LFO on the spatial map
- [ ] Backend computes per-device gains from `installation.json` positions and sends
      `/gain` (or a dedicated `/sgain` to leave manual gain independent) at ~20–30 Hz
- [ ] Synced start of a named sample on all devices via `/cue`
- Zero Pi-side changes; works with existing patches.

Stage B — Pi-computed (later, for 50–100 devices / dashboard independence):
- broadcast `/point <x> <y> <radius>` per frame; each Pi computes its own gain from its
  own position. Sketch the OSC shape in `osc-schema-contract` now; implement later.

Done (Stage A) when: a sound sweeps across a real multi-Pi installation, authored from
the dashboard map.
