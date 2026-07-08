# spatial-1-authoring-ui

Authoring surface for spatial-0's engine on the dashboard spatial map.

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
