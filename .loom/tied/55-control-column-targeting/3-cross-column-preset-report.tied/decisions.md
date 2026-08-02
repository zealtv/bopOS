# decisions — 3-cross-column-preset-report

## The answer (Bob, 2026-08-02)

> this was a misinterpretation on my behalf. if i have a column targeting all,
> and a column targeting a group, changing the preset in all also changes it
> for the group. this makes sense.

**There is no scoping defect.** The report is the overlap case the
measurement predicted: one column on `addColumn()`'s `["all"]` default and one
on a group, with the group's seats inside All. The preset was applied to every
seat, so both columns reported it — correctly.

This closes the question the stitch existed to ask. The apply path
(`control-host.js:135` → `server.py:2043` → per-seat `applied_preset`
provenance at `control-surface.js:284`, filtered per column at
`control-column.js:142`) is scoped end to end and stays as it is. Nothing to
fix, nothing to hunt.

## What is NOT ruled

The stitch offered two legibility items on the overlap branch. Bob did not rule
on either — he called the behaviour sensible and stopped there, so neither is
authorized work:

1. **`addColumn()` defaults to every seat in the venue.** Whether that is the
   right default depends on whether a column is an *arrangement*, which is
   exactly the open question in `2-multi-target-model`. It belongs there, not
   here.
2. **A card gives no cue that its state answers a wider target than its own
   column's.** Bob read the overlap correctly without one, which is evidence
   against urgency, not against the idea.

Neither is carried forward as a loose end. If `2-multi-target-model` changes
what a column *is*, revisit item 1 there; item 2 is a UI question that needs
Bob to want it first.

## Consequence for the thread

`55-control-column-targeting` now has one live defect, `1-column-scroll`
(claimable), and one open Bob question, `2-multi-target-model` (`.waiting`).
The cross-column preset report is not part of either.
