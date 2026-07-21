# 22-listener-range-ux

Rework how the listener's range is set on the Seats spatial map.

Authorized by lore item `2026-07-21-show-console-dock-and-fixes-braindump`.
Bob, 2026-07-21:

> On the seats page, the listener widget — I want us to find a way to expand and
> contract the listener range. Currently we drag that widget out, that little sort
> of knobbly line; I'd like that interaction to be constrained to the listener dot
> itself. The issue is that if the listener is, for example, up at the top of the
> map, I can't extend its listening distance because it clips the map. So we need
> some sort of interaction on the listener that lets us dial in and out the
> listener range, and perhaps indicate it in another way other than the line —
> some sort of gradient with a thin line around the outside, or some sort of
> outline that shows the maximum range... That's a bit of a design challenge, so
> that is one to put to a UX/UI expert to ideate on and come up with a good
> solution.

## The defect, concretely

In `dashboard/static/js/spatial.js`, the `.listener-tip` handle drag
(`headingDrag`) sets **both** `listener.heading` and `listener.range` from the
pointer's distance to the listener body. Range is therefore only reachable by
dragging a handle that lives `range` metres away from the listener — which leaves
the map when the listener sits near an edge, making large ranges unsettable.

## Shape of the work

1. `01-listener-range-design` — UX proposal. **Bob ratifies before implementation.**
2. `02-listener-range-implementation.waiting` — build the ratified design.

Do not implement past the unratified design (house rule: facilitator/user-facing
design is a Bob gate).
