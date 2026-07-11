# spatial-1-authoring-ui

> **RE-SCOPED 2026-07-10 (seam council). `.waiting` on
> `patch-seam/seam-3-points-node-side` tying** — the wire and node-side
> decomposition this UI drives. Authority: `.loom/tied/seam-0-council/`.
> Scope is now "author/move the point *set*" (arbitrary count, each point =
> x,y + radius + falloff enum). There are no dashboard-computed per-device
> gains — to visualise the sweep, mirror the node math (shared falloff module)
> for display only, or read simfleet's logged values; never send the result.
> The motion drivers (`path`/`orbit` from the reverted `dashboard/spatial.py`,
> commit `0ce8821`) are the salvage for procedural movement. Checklist below
> re-read through that lens (per-device-gain visualisation bullet → mirrored
> display math).

Authoring surface for the spatial point set on the dashboard spatial map.

> Bob's multi-element UI direction (2026-07-11): element dots coloured by
> element index, numbered by device — see the note in
> `patch-seam/seam-3-points-node-side/instructions.md`. If this stitch touches
> how devices/elements render on the map, follow it.

- [ ] A draggable automation point on the SVG map: position, radius ring,
      falloff curve picker, on/off.
- [ ] Simple motion authoring: drag records/streams live; plus at least one
      procedural mover (LFO orbit or A→B path with rate). Keep it minimal —
      the scene language (paused thread) is the real authoring surface later;
      don't build a sequencer here.
- [ ] Visualise computed per-device gains on the map (dot intensity/size) so
      the sweep is legible without audio — this is also the demo Bob sees.
- [ ] Facilitator view: **do not add spatial controls there without Bob** —
      user-facing facilitator changes are a decision gate (CLAUDE.md).
- [ ] verify_*.py Playwright: drag the puck, assert gain redistribution;
      remember the three Playwright gotchas in CLAUDE.md (scroll-before-drag
      especially — this is exactly the spatial-drag case).
