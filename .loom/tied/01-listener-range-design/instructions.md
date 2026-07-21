# 01-listener-range-design

Bob asked for this one to go to a UX/UI expert to ideate. Produce a proposal with
real alternatives, recommend one, surface it to Bob, mark this stitch `.waiting`,
and tie it with the ratified design as `decisions.md`.

## The problem

Setting listener range by dragging a handle positioned at range-distance is
unbounded by the map: near an edge the handle clips out of the viewport and large
ranges become unsettable. Range and heading are also conflated in one gesture
(`headingDrag` in `dashboard/static/js/spatial.js` writes both).

## Requirements Bob stated

- The range interaction is **constrained to the listener dot itself** — no handle
  that travels away from it.
- Range is **indicated** some other way than the knobbly line: he suggested a
  gradient with a thin outline, or a plain outline circle showing maximum range.
- Heading must remain settable; the two controls should read as distinct.

## Requirements the system imposes

- The listener puck only renders when `installation.simulation.active` — the
  design must work in the simulation context it lives in.
- Range clamps to `[LISTENER_RANGE_MIN, room diagonal]` today. Decide whether the
  new interaction keeps that ceiling, and how a range larger than the visible map
  reads.
- Touch as well as pointer: the Seats tab is used on a laptop, but a dial or
  scrub gesture on a small target needs a touch answer. There must also be a
  keyboard/numeric path — a typed range field in the inspector is a legitimate
  part of the answer.
- The wire is unchanged: `set_listener` still carries `x`, `y`, `heading`,
  `range`. This is a UI change, not a contract change.
- Live feedback during the gesture (the current code updates the SVG directly
  before sending) — don't regress to send-on-release only.

## Deliver

- At least three sketched alternatives (e.g. scrub-on-dot, a ring you grab
  anywhere on its circumference, a rotary dial on the dot, an inspector numeric
  field with a passive range ring), each with its failure modes at map edges,
  at extreme ranges, and on touch.
- A recommendation with reasoning.
- The visual treatment for the range indication in **both themes**, coordinated
  with `21-theme-cyan-tint` if that lands first.
- `decisions.md` in this stitch once ratified; keep the full proposal as a lore
  item if it is substantial.
