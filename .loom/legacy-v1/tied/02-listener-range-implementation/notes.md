# Verification notes — 02-listener-range-implementation

`verify_listener_range.py` (this directory), run from `~/.venvs/bopos`:
**31/31 checks pass.** Screenshots: `shot-top-edge-max-range.png`,
`shot-heading-vs-range.png`.

Fixture: 4x3 m room (exact 5.0 m diagonal), listener at **(2.0, 0.1)** — hard
against the top edge — with range 1.0.

Cases covered:

- **The case that failed today.** With the listener glued to the top wall, a
  collar scrub *downward into the room* takes range all the way to the 5.0 m
  ceiling. The pointer never leaves the map. Heading and position are untouched;
  the outline goes `at-max` solid and the readout says `(max)`.
- **Inward scrub** on the same collar pulls range back down.
- **Heading without range**: dragging the tip sets heading (0 → 90) and leaves
  range at 2.5. The tip stays at a fixed 0.9 m from the body throughout.
- **Range without heading**: collar scrub, wheel-equivalent nudges, typed value
  and arrow keys all leave heading exactly where it was.
- **Round-trip**: `set_listener` → reload → value intact; reconnect after the
  gestures restores range *and* heading; on-disk `installation.json` agrees.
  The listener object still carries exactly `{x, y, heading, range}`.
- **Numeric path**: typed range commits and clamps at the diagonal; typed
  heading commits without touching range.
- **Keyboard path**: puck takes focus, `ArrowUp` ×2 nudges +0.1 m each (proving
  focus survives the heartbeat re-render), `Shift+ArrowRight` turns 15°.
- **Touch path**: real CDP `Input.dispatchTouchEvent` drag on the collar raises
  range and leaves heading alone.
- **Theme**: `--listener-field`/`--listener-ring` resolve to `--sim` and are
  confirmed distinct from `--green`, so `21-theme-cyan-tint`'s retune carries.

Two Playwright wrinkles worth remembering:

1. The heading tip sits a fixed 0.9 m out; with the listener against the top
   wall and pointing north that lands **outside the SVG viewport** (the map pad
   is only 0.6 m), so it is not hittable. The aim tests move the listener to
   y = 1.5 first. This is a real property of the ratified fixed handle, not a
   bug in the test — and it is precisely why range no longer lives on the tip.
2. `element.focus()` on the SVG puck can no-op on the first call right after a
   websocket-driven re-render; the guard retries focus in a short loop.

Other tied suites: the repaired `2-range-widget` guard passes in full
(13/13). `07-seats-workspace` has 3 pre-existing failures unrelated to this
work — see `decisions.md`.
