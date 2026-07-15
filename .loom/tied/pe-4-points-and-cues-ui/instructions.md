# pe-4-points-and-cues-ui

The editor's points mini-setup and cue firing (ratified design:
`.lore/items/2026-07-14-patch-editor-design-ratified/`, proposal §6–§7).
Needs pe-3 tied (cue buttons render declared cues from the manifest editor's
data).

- Points: reuse the spatial map component stripped to one element pinned at
  the origin, **placed at the centre of the box, not the corner** (Bob,
  2026-07-14 — points must be able to approach from every side), with the
  existing point authoring controls (drag, radius, falloff). Frames go out the normal `/pt` wire; the rig's existing
  decomposition delivers per-element proximity to the single instance.
  Session-only scratch (Q3 ratified) — never persisted to
  `installation.json` or anywhere else. No listener puck (one source,
  identity stereo).
- Cues: one fire button per declared cue (immediate fire through the normal
  `/cue` path) plus a free-text fire box for trying ids before declaring
  them.
- Mind the three Playwright spatial-drag gotchas in CLAUDE.md (scroll reset,
  clamped drag targets, single dialog handler).
- Verification: Playwright suite — drag a point and assert the `/pt`
  per-element values arriving at a capture socket; fire a declared and an
  undeclared cue and assert `/cue` delivery.
