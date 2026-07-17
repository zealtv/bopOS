# 2-range-widget

Make the listener heading widget's pull-out distance control the audition
falloff range. Requires `1-forward-bias` tied first (shared geometry file,
avoids churn).

## Current state

- `dashboard/static/js/spatial.js`: listener puck with a heading line and
  tip at a fixed 0.72 radius; dragging the tip (`headingDrag`) sets only
  `listener.heading`, then `send("set_listener", …)`.
- `dashboard/server.py` `set_listener` → `state.clean_listener` →
  `osc_bridge.send_audition_listener`, which currently sends `range_m` as
  the **room diagonal** (fixed) in the 4-value `/audition/listener` frame.
- `python/audition_geometry.py` validates `range_m > 0`.

## Design (pinned)

- The tip's distance from the listener centre in room metres IS the range:
  dragging the tip sets both `heading` (angle, as now) and `range`
  (radial distance). Persist `range` on the listener object
  (`{x, y, heading, range}`) through state, websocket broadcast, and
  installation persistence.
- Clamp: minimum 0.5 m; maximum the room diagonal. Default when absent
  (older persisted state): the room diagonal — exactly today's behaviour,
  so existing installations sound unchanged until someone drags.
- `clean_listener` validates/clamps `range`; `send_audition_listener` sends
  the listener's range instead of computing the diagonal (keep the diagonal
  as the fallback for missing/invalid range).
- Render the heading line/tip at the true range radius so the widget reads
  as "how far I can hear" on the map. Keep the tip hit-target usable when
  range is small (min visual/hit radius may exceed 0.5 m visually — hit
  target may be styled larger than the geometry, but the stored range is
  the dragged distance).
- Do not change the `/audition/listener` frame shape — same 4 values.

## Verification

Dashboard stitch ⇒ Playwright `verify_*.py` in the stitch directory: copy
the newest tied dashboard verify (`ls -t .loom/tied/*/verify_*.py`) as the
template — repo-by-marker root, sim ports, teardown, and the three
documented Playwright gotchas (scroll-reset before spatial drags, clamp
drag targets on-screen, one type-aware dialog handler). Drive: enable
simulation, drag the tip outward, assert the broadcast listener carries the
new range and that the audition-relay-bound frame (or state) reflects it;
drag inward below 0.5 m and assert the clamp. Run from `~/.venvs/bopos`
venv per CLAUDE.md.
