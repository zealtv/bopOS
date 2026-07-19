# p5-inspector-defaults

Two small inspector shape changes.

1. **Then-actions default to one non-deletable row, defaulting to stop.**
   A step always shows at least one then-action row; the first row has no
   Remove button. Model: a new step's `then_actions` is `[{"type":
   "stop"}]` rather than `[]`; loading a legacy step with an empty list
   normalizes to the same (the engine already treats empty as stop, so
   behavior is unchanged — this is authoring-surface truth-telling).
   "Add row" still appends further rows; rows beyond the first delete as
   today. The "No rows means stop" hint goes away.
2. **Message inspector target section becomes collapsible.** The chip
   picker (All toggle, group swatches, seat roster) is the tallest block
   in the message inspector; collapse it behind a summary line showing the
   current selection in terse wire form (e.g. `3+7+g1`), expanded on tap.
   Default collapsed when the message already has a target, expanded for
   a fresh message. Greyed-for-/cue//pt behavior unchanged.

Verify: `verify_show_inspector_defaults.py` (house pattern): new step
shows exactly one stop row without a Remove button; adding then removing
a second row returns to the non-deletable single row; legacy show with
`then_actions: []` renders the default row and saves normalized; target
section collapsed summary matches the wire preview, expands to the chip
picker, edits still land. Amend tied 5/5c expectations if selectors moved
(log it).
