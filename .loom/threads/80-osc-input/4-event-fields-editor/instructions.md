# 4-event-fields-editor

Dashboard authoring and firing for typed fields, per `1-typed-event-fields.tied/proposal.md`:

- Patch editor (`dashboard-patches.js`): an event's field list edited like
  the param list — name, kind, range/options, default, an "optional" checkbox.
- Event fire controls (`show.js`, control surface): the same control per kind
  that params use, labelled by field name.

Verify with a `tests/verify_*.py` journey (glean `playwright-gotchas`).
