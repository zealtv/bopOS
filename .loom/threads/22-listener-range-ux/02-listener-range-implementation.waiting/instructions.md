# 02-listener-range-implementation

**Waiting on `01-listener-range-design` being ratified by Bob.** Claim then.

Build the ratified listener-range interaction in
`dashboard/static/js/spatial.js` + `dashboard/static/css/style.css`.

## Outcome

- Range is settable with the listener anywhere on the map, including hard against
  an edge, up to the design's ceiling.
- Heading remains settable and the two gestures do not collide — dragging one
  never silently changes the other (today `headingDrag` writes both).
- The range indication renders per the ratified design in both themes.
- Live feedback during the gesture is preserved; `set_listener` still carries
  `x`/`y`/`heading`/`range` — no contract change.
- Existing tied spatial suites pass; update any that grab `.listener-tip` and say
  what changed.

## Verify

Playwright per `CLAUDE.md`, minding the spatial-drag gotchas: `window.scrollTo(0,0)`
and re-read bounding boxes before dragging (gotcha 2), clamp drag targets on-screen
because the room can extend above the viewport, and use a one-shot
`page.evaluate` `scrollIntoView` plus a fresh `bounding_box()` rather than
`scroll_into_view_if_needed` (gotcha 6).

Cases: set a large range with the listener at the top edge of the map (the case
that fails today); set heading without perturbing range and vice versa; round-trip
the value through `set_listener` and a reload; touch-emulation path; keyboard/
numeric path.
