# 6-text-kind-control

A styled control-panel component for the `text` kind. **Deferred** — Bob,
2026-07-28: "we currently don't have any UI for strings. That can be put off
to later but if strings are in the contract, they should be implemented in the
manifest and given styled control panel components in the future." The
manifest half is not deferred; it lands in child `2`.

Kept in this thread at Bob's instruction rather than moved to
`desktop-ui-overhaul`.

## Actual starting state (measured, not assumed)

There is an **unstyled** control, not no control. `control-surface.js` maps a
string declaration to a `"string"` shape (line 282) and renders a plain
`<input type="text">` (line 352), while excluding it from aggregation and
automation (lines 64, 101). What is missing is the ratified design language:
the tied `6-non-float-kinds` slice covered toggle, integer, enum, and event
and **skipped strings entirely**.

## Scope

- A text row in the control-panel design language — authority is the tied
  `2-control-panel-design` (`control-panel-design.md` §2 kind table and
  `design-language.md`). Extend that table with the text kind rather than
  inventing a parallel treatment.
- Decide and document the questions the other kinds answered: commit on blur
  or on Enter (the precision-field precedent in
  `dashboard/static/js/precision-field.js` is the nearest idiom); what "mixed"
  looks like across an aggregate target, given text params are currently
  excluded from aggregation; whether a max length belongs in the manifest.
- Text takes **no generators** — it is not numeric, and §3.2 automation is a
  numeric grammar. Keep it out of the ∿ drawer, as today.

Coordinate with `desktop-ui-overhaul/02-app-wide-rollout-design`: if that
stitch lands first, the text row adopts whatever it ratified for text inputs
app-wide instead of specifying its own.

Verify: extend the living control-surface journey with a text param — render,
edit, commit to the wire via simfleet, and survive a heartbeat re-render
(the re-render trap that `46-control-surface-probe-race` and the
`interacting` guard both exist for).
