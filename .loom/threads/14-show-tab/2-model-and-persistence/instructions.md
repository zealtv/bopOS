# 2-model-and-persistence

Backend data model + persistence + edit surface for shows. Requires the
design note from `1-design-and-schema` (`.notes/show-tab-design-2026-07-18.md`).

Scope:

- New separable module (suggested `dashboard/show_model.py` or a
  `dashboard/show/` package — follow the design note) implementing the show
  schema: steps, dividers, messages, uids, aliases, durations, play counts,
  then-actions, forward-sync flag. Section derivation from dividers lives
  here (pure functions, unit-testable).
- Load/save to the location the design note fixed; atomic writes consistent
  with existing dashboard persistence; survives restart; tolerates a missing
  or empty show file (empty show).
- Edit operations as functions the WS layer will call: create/delete/move
  step and divider; set step properties; add/remove/reorder messages; set
  message properties. Every mutation persists and returns the new state.
- Wire the WS surface from the design note into `server.py`/`osc_bridge.py`
  for CRUD + full-state show broadcast to clients (playback commands are
  stitch 3; UI is stitch 4 — this stitch may verify WS round-trips headless).

Verify: `verify_show_model.py` in this stitch dir, headless (no Playwright)
— venv `~/.venvs/bopos`, repo located by marker. Cover: schema round-trip,
section derivation with edge dividers, mutation ops, restart persistence,
WS CRUD round-trip against a running server on non-default ports.
