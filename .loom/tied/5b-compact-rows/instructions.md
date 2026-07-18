# 5b-compact-rows

Bob reviewed screenshots of the shipped stitch-4/5 UI (2026-07-18) and wants
the step table much denser — **Ableton session-view scenes and QLab cue
lists are the explicit guides**. The point of the table is seeing a large
composition at a glance; the inspector owns the details.

Scope (frontend only — `show.js` + `style.css`; no schema or backend
change):

- **Rows become short.** One compact line per step, Ableton-scene height,
  not the current tall card. Dividers stay slim. Dense-layout check: dozens
  of steps should fit a 768×1024 viewport.
- **Transport controls become small icons.** Play/stop/pause/next-action as
  compact icon buttons (inline SVG or unicode glyphs consistent with
  existing dashboard iconography), state shown by icon swap/colour, not
  words. Keep hit targets touch-usable despite the density (QLab manages
  this; ~40px minimum touch target can overlap a visually smaller glyph).
- **Drop from the row:** play-n-times, then-action summary, and the
  duration long-form. Those live in the inspector now. Keep at most: icon
  cluster, alias, message pills, a terse duration (e.g. `1m30`), and the
  remaining-time countdown while playing/paused.
- **Colour-coded message pills.** A message's pill colour derives from its
  alias (fallback: address) via a stable hash into a distinguishable
  palette, so the same alias reused across steps is identifiable at a
  glance. Same alias ⇒ same colour everywhere, across steps and sessions.
  Respect the existing dashboard palette idioms (GROUP_SLOTS colours are
  precedent) and keep contrast/legibility in the dark theme; unaliased
  messages stay neutral.
- Keep focus behaviour, inspector binding, empty state, and transport strip
  working unchanged.

Verify: extend/copy the stitch-4 Playwright verify as
`verify_show_compact.py` in this stitch dir — assert row height budget
(e.g. a seeded 20-step show fits without scrolling past N px), icon
buttons drive start/stop, pill colour equality for same alias across two
steps and inequality for different aliases, and no page errors. Re-run the
tied stitch-4 and stitch-5 verifies afterwards; update any of their
selectors/expectations broken by the redesign (note what changed in the
worklog — amending a tied verify is fine when the UI legitimately moved).
Save before/after screenshots into this stitch dir as artifacts.
