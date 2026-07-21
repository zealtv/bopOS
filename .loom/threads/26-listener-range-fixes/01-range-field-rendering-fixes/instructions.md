# 01-range-field-rendering-fixes

Fix the three range-field rendering defects Bob found (parent `instructions.md`
states them; read it first). All three live in
`dashboard/static/js/spatial.js` and `dashboard/static/css/style.css`.

## 1. Clip the range indication to the room

Bob: the radius must not draw outside the room rectangle.

- `.listener-ring-outside` (`spatial.js:159`, `style.css:158`) is the dashed
  out-of-room arc the tied design added on purpose. Bob's ruling supersedes it.
  Simplest reading: drop that element and keep only the clipped ring + field.
- Check the room clip itself — `#spatial-room-clip` is applied to the inner `<g>`
  (`spatial.js:157`) yet the screenshot shows a solid arc surviving outside the
  room at bottom-right. Confirm the clip path geometry actually matches the room
  rect at the current viewBox before concluding the clip works.
- Range still clamps to the room diagonal (`clampRange`, Bob's ruling 2 in the
  tied `01-listener-range-design/decisions.md`); clipping is a *drawing* change,
  not a clamp change. Do not touch `state.py:733`.
- The residual magnitude tick (`.listener-tick`) is drawn inside the puck group
  and is unclipped — decide and state whether it should clip too (it can also
  leave the room). Prefer consistency: if the ring clips, the tick clips.

## 2. Repair the radial gradient

The wash currently appears only in the quadrant down-and-right of the puck,
squared off at the listener's x/y. Diagnose first — screenshot the DOM/computed
geometry, don't guess — then fix. Prime suspect is the `radialGradient` at
`spatial.js:148-151` using the `objectBoundingBox` default under a translated
`<g>` and a clip; `gradientUnits="userSpaceOnUse"` with explicit `cx`/`cy`/`r`
matching the listener position and range is the expected shape of the fix, and
it must be updated in `paintRange()` alongside the circle radii.

The three stops and their alpha tokens (`--listener-field-a`, `-mid`,
`style.css:150-154`) are ratified; keep the visual intent (dense at the
listener, fading to nothing at the range edge) in both themes.

## 3. Make the field follow the listener drag

`spatial.js:415` retransforms only `listenerDrag.group` (the puck).
`.listener-range-field` keeps its render-time `transform` (`spatial.js:155`) and
lags until drag-end re-render. Move the wrapper — and, if the gradient becomes
`userSpaceOnUse`, its `cx`/`cy` — in the same mousemove branch. Factor a small
helper so render, drag, and `paintRange()` agree on one placement path rather
than three.

Also check the keyboard listener-move path (`spatial.js:~293`) and the range
wheel/keys for the same lag.

## Verify

- Playwright verify in this stitch directory (copy the newest tied dashboard
  guard as the template; CLAUDE.md lists the Playwright gotchas — especially
  (2) scroll-then-measure for spatial drags and (9) one scroll state per
  measurement).
  - room 10 × 8, simulation active, range at the diagonal max: assert no part
    of `.listener-field` / `.listener-ring` paints outside the room rect
    (compare bounding boxes in one `page.evaluate`).
  - assert the gradient covers all four quadrants around the puck — e.g. sample
    the fill geometry, or assert the gradient's resolved centre equals the
    listener position.
  - drag the listener across the room and assert the range field's centre
    tracks the puck **mid-drag**, not only after mouseup.
- Before/after screenshots in this stitch directory, dark and light.
- `.loom/tied/22-listener-range-ux/` and its child stitches: any guard that
  asserts the dashed out-of-room arc exists is now **superseded**. Invert or
  repair it in place with an inline comment naming this stitch, and record the
  supersession in this stitch's `decisions.md`.

Leave `#listener-bar` alone — stitch `02` retires it.
