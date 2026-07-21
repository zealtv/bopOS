# decisions — 01-range-field-rendering-fixes

## Defects 1 and 2 were one bug, not two

The stitch was written expecting two independent fixes: a clipping problem and a
gradient problem (with `gradientUnits="userSpaceOnUse"` named as the likely
gradient fix). Diagnosis found a single root cause for both, and the gradient
needed **no change at all**.

`clipPathUnits` defaults to `userSpaceOnUse`, which resolves in the coordinate
system of the element *referencing* the clip path — not the coordinate system the
`clipPath` was defined in. The clipped group sat inside
`<g class="listener-range-field" transform="translate(listener.x listener.y)">`,
so the room-shaped clip window was slid by the listener position. Its top-left
corner landed exactly ON the listener, which is why:

- the wash appeared only down-and-right of the puck, squared off at the
  listener's x and y (defect 2 — that square edge is the clip window's corner,
  not a gradient artifact); and
- a solid arc survived outside the room at bottom-right (defect 1 — the window
  extends past the room's right/bottom walls by the listener offset).

Measured before the fix, with the listener at (5, 4) in a 10 × 8 room: the clip
window was offset from the room rect by `[336.4, 269.2]` screen px against a
scale of 67.3 px/m — i.e. exactly (5 m, 4 m). That number is the proof.

**Fix:** the clip moves to an untranslated wrapper and the `translate` moves to an
inner `.listener-range-at` group. The `radialGradient` keeps its
`objectBoundingBox` default, which was always correct — the circle's bounding box
is centred on the circle.

## The dashed out-of-room arc is retired (supersession)

`.listener-ring-outside` (JS + CSS) is deleted. The tied `22-listener-range-ux`
design drew it deliberately so the true circle stayed legible past the wall;
**Bob's 2026-07-21 ruling supersedes that** — the range indication clips to the
room, full stop.

Repaired in place, per CLAUDE.md "Re-running a tied guard", in
`.loom/tied/02-listener-range-implementation/verify_listener_range.py`:

1. the `dashed` probe now asserts `.listener-ring-outside` is **absent** rather
   than present at r = range (assertion inverted, inline comment names this
   stitch);
2. the `clipped` probe read `.listener-field`'s immediate `parentNode`; the clip
   now lives one level up by design, so it reads
   `closest('[clip-path]')` instead.

That guard is green again: 32/32.

## The magnitude tick now clips with the ring

The stitch asked for a decision. **The tick clips.** It moved out of the puck
group into the clipped range group, on the reasoning that it is a range
indication, not part of the puck — so it should obey the same rule as the ring.
The alternative (an unclipped tick over a clipped ring) would reintroduce
exactly the inconsistency Bob objected to, at smaller scale.

## One placement path

`placeListener(svg, listener)` sets the same transform on the puck and the range
group, and is called from render, from `paintRange()`, and from the drag
mousemove. This is what fixes defect 3: the drag previously retransformed only
`listenerDrag.group`. Keyboard/wheel range changes route through `paintRange()`,
so they inherit it.

## Not touched

`clampRange` and `state.py:733` — clipping is a drawing change, not a clamp
change (stitch instruction). `#listener-bar` — stitch `02` retires it.
