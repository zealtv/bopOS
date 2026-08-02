# 2-multi-target-model

> shouldn't it remain as a single control panel, that is targeting all seats
> from it's target picker? — Bob, 2026-08-02

**`.waiting` on Bob.** This reverses a decision that shipped nine days ago, so
it is his to make, not a bug to fix. The question is small; the consequences
are not, and they are laid out below so the ruling can be made once.

## What shipped, and why

`07-target-selector-component` (tied 2026-07-30) states the current behaviour
as an explicit ruling: on the Control surface a mixture renders **a card per
selected entry**. `control-column.js:368-376` does exactly that —
`selection.map(selectedCard)` — with the one exception that `all` collapses to
a single `All Seats` card.

The machinery for the alternative already exists and is used by that exception.
`liveCard(scope, item, members, …)` takes a **member list**, and
`aggregateValue` (`control-surface.js:80`) already reduces N seats to one
control with a `mixed` state, a mixed hatch, and mixed automation. That is what
an `All` card and a group card have always been. So "one panel targeting the
whole selection" is not new machinery — it is applying the machinery the `all`
card already uses to an arbitrary selection.

## The case for one panel (Bob's reading)

* It is what the target picker's own summary already says. A column titled
  `Front+Back+Wide` that then renders three separate panels contradicts its own
  title.
* It matches every other multi-target surface in the app: `all` and a group are
  both already "one panel, N seats".
* It makes the column a fixed height regardless of selection size, which is a
  large part of why report 1 was noticed at all.
* Bob's stated workflow — *make some columns, target some groups, apply some
  presets, click capture step* — reads as one column = one arrangement. Three
  panels inside one column is a third level of nesting that workflow has no
  use for.

## The case for cards-per-target (what shipped)

* Two groups with different values show *as* different values; one panel shows
  `mixed` and hides which is which.
* A per-card preset is meaningful; a preset applied to a mixture is one apply
  across everything, which may be what Bob wants but is a different act.
* Per-seat cards carry per-seat state that has nowhere to go in an aggregate:
  online/offline dot, `empty-group`, the Remote-only device commands, the
  per-card overflow.

## The question, precisely

Not "one panel or many" in the abstract, but: **when a column's selection is a
mixture, is the panel an aggregate over the union of member seats, and does
anything survive per-entry?**

Three shapes, cheapest first:

* **(a) Pure aggregate.** One card, members = union of every selected entry's
  seats, `mixed` where they differ. Deletes the most code. Loses per-entry
  identity entirely — the column can no longer tell you that Front is at 0.3
  and Back at 0.7, only that they differ.
* **(b) Aggregate with per-entry disclosure.** One card by default, with the
  selected entries listed in the head and expandable when you need to see them
  apart. Keeps both readings; costs a new affordance inside an already dense
  342px column.
* **(c) Keep cards, fix the scroll.** `1-column-scroll` alone. The status quo
  becomes usable and this stitch drops.

I recommend **(a)** if Bob's workflow answer is "a column is one arrangement",
which is what his message reads like. (b) is the hedge and I would rather not
build it speculatively.

## What the ruling has to decide with it

1. **Presets on a mixture.** A preset applied to an aggregate is one apply
   across the union. `apply_preset` takes a single `{scope, id}`, so an
   aggregate over two groups is not currently expressible on the wire at all —
   it would be N applies, or a widened verb. Note that `4-n-columns/2` went
   deliberately the *other* way for capture (venue-wide, `scope` removed from
   the wire entirely) on the grounds that widening the server vocabulary was
   the cost of the per-column answer. Do not widen it back without saying so.
2. **The applied-preset readout.** Provenance is per seat
   (`control-surface.js:284`). An aggregate over seats with different
   `applied_preset` values is `mixed` — which is already handled, and is
   probably the honest answer to report 2 as well.
3. **What a new column defaults to.** `addColumn()` defaults to `["all"]`
   (`control-host.js:210`). That default is the most likely explanation for
   Bob's "a preset in either column effects all columns" — an All column
   correctly reflects a preset applied to any group inside it. If columns are
   arrangements, a new one starting as "everything" may be the wrong default.
4. **Capture.** `4-n-columns/2-venue-wide-capture` made capture venue-wide and
   argument-free by ruling, precisely because a per-column scope captured the
   wrong thing for three of five column shapes. Bob's workflow sentence ends
   with "then click capture step", which is consistent with that — but confirm
   it, because if a column is an arrangement it is tempting to re-read capture
   as per-column, and that argument was already had and settled.

## Before implementing anything here

Read, in order: `4-n-columns/1-columns-design/decisions.md` (the nine ratified
decisions, D1 and D5 especially), the `07-target-selector-component` tied
record for the card-per-entry ruling, and `4-n-columns/2-venue-wide-capture`
for why capture takes no scope. This stitch reverses part of the first and all
of the second's premise if it is not careful.
