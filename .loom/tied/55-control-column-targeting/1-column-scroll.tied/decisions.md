# decisions — 1-column-scroll

## The fix

`css/control-column.css`: the cards track goes
`minmax(0, max-content)` → `minmax(0, 1fr)`. One declaration.

The diagnosis in the instructions was correct and is confirmed by measurement:
with `align-content: start` there is no compression step, so a `max-content`
track takes its growth limit regardless of the container's `max-height`. The
body's `overflow-y: auto` was therefore inert — `clientHeight === scrollHeight`
— and the overflow escaped the column to be clipped silently by the host's
`overflow-y: hidden`.

## The constraint the instructions warned about is FALSE, and that is the finding

The instructions said to preserve this, quoting `control-column.css:36-46`:

> `max-height:100%` resolves against the tab's definite row height and to
> nothing at all on Remote, where the column's parent has no definite height —
> so the single-column host keeps growing with the page as it always did.

**Remote has never behaved that way.** Measured on `/facilitator` at 1440 × 900
with a 40-param manifest, *before* any change:

```
cardsClient 501   cardsScroll 1242   columnHeight 640   docScroll 900   viewport 900
```

The column is clamped well inside the viewport, its body is already a working
scrollport, and the document does not scroll at all. The cause is
`facilitator.css:25` — `#control-column-host{flex:1;min-height:0;overflow-y:auto}`
inside a `height:100%` flex body, which is a *definite* height by a different
route than the Control tab's. So both hosts were always definite, and the
comment's distinction between them was fiction.

This matters beyond the comment: the instructions treated "Remote must keep
growing with the page" as the hazard that could veto `1fr`. That hazard never
existed. What replaced it is a plain regression question — does `1fr` change
Remote? — answered by measurement below.

The instructions' own framing was right about the class of defect while being
wrong about which half: they flagged the Control sentence as false and told me
to trust the Remote sentence. Both were false. This is the `52` pathology
(correct-looking code with a sincere comment claiming a guarantee it never
gave) and the lesson is that the *second* half of a comment already proven
unreliable does not inherit credibility from having been quoted approvingly.

## Remote is unchanged, to the pixel

Identical metrics before and after the fix:

```
before   cardsClient 501   cardsScroll 1242   columnHeight 640
after    cardsClient 501   cardsScroll 1242   columnHeight 640
```

This satisfies **Bob's ruling of 2026-08-02**, given while this stitch was in
flight:

> remote works - and i like that it separates each target - i don't want that
> behaviour to change whilst we work on the control tab

Recorded here because it binds `2-multi-target-model`, not this stitch:
`ControlSurface` and `control-column.css` are **shared** between the Control tab
and Remote, so a single-target or aggregate column — which all three consultants
recommended — propagates to Remote unless it is actively prevented. Remote
keeping card-per-target is now a constraint to be designed for, not a default.

## Declined: the horizontal counterpart

The instructions asked whether `#control-column-host`'s `overflow-y: hidden`
should also change, since it is what turned a visible overflow into an invisible
one. **Left alone.** With the track fixed, the column no longer overflows its
host at all (asserted: `columnHeight <= hostHeight`), so the `hidden` is now
unreachable rather than harmful. Changing it would only matter if something
overflowed again — and the guard fails first in that case, which is the better
signal than a scrollbar appearing on the tab.

## Deviation: a dedicated guard file

The instructions said to put the check in `tests/verify_control_tab.py`, the
nearest journey. It is instead `tests/verify_control_column_scroll.py`.

Reason: forcing the overflow from the manifest (which the instructions rightly
required, so the guard survives `2-multi-target-model`) means a 40-param
fixture, and `verify_control_tab.py` is a 747-line journey whose fixture carries
one param. Forty would change every card's height in a file full of clicks and
bounding-box reads. Nothing there counts param rows, so it would *probably*
survive — but "probably" against 747 lines of unrelated assertions is a bad
trade for file tidiness. The new file follows the same harness idiom
(repo-by-marker, free ports, real server + simfleet, teardown).
