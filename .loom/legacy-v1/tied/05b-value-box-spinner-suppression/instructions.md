# 05b-value-box-spinner-suppression

The value box has one face and two appearances. Fix the component, not the
surfaces.

Bob's observation, 2026-07-30: numeric entries show native inc/dec spinner
arrows, "they behave well in the generator drawer — it should be the same value
box throughout."

The drawer is the one behaving correctly, by a **local** rule that predates the
component. `control-panel.css:1360-1368` suppresses spinners on `.live-gen-num`
only, and only inside `:is(.live-card,.device-control,.show-inspector-section)`:

    appearance:textfield; -moz-appearance:textfield;
    ::-webkit-outer-spin-button, ::-webkit-inner-spin-button { -webkit-appearance:none }

`css/value-box.css` — the component face `05-value-box-component` extracted —
sets width, height, padding, border, tabular numerals and float/integer
alignment, and says nothing about spinners. So every numeric entry outside the
drawer (manifest editor, Seats, event lead, Show inspector fields) still paints
arrows inside a 58px box while the drawer's do not.

Nothing in `05`'s `decisions.md` or the ratified `design-language.md` mentions
spinners, so this is not a superseded ruling — it is an unstated inheritance
`05` did not sweep up. That makes it a defect in the component's definition.

Work:

- Move the suppression onto the component in `css/value-box.css`, so it travels
  with the face to every current and future consumer.
- Delete the scoped `.live-gen-num` rule. Leaving it is the same mistake in
  miniature that gave the app two token layers — a rule living on a surface
  instead of on the component.
- Check the scoping assumption before assuming parity: the old rule only fires
  inside those three containers, so any drawer rendered elsewhere already shows
  spinners today. Grep rather than assume.
- **Confirm keyboard ↑/↓ still steps.** `appearance:textfield` removes the
  buttons; it must not remove the step behavior the integer/`step` declarations
  rely on (event lead steps 50, not 1). This is the only real risk here.
- Extend `tests/verify_value_box_component.py` rather than adding a new module —
  it already owns the component's shipped contract.

Sequenced before `06-control-panel-reflow-and-editor` deliberately: `06`
reflows and re-shoots the surfaces that would otherwise be captured with
spinners still showing, and `07`/`09` add further consumers of the same face.
Fixing the component before its next adopters is cheaper than after.

Not this stitch: any other divergence between value-box consumers, and any
change to the 58px geometry or alignment rules `05` ratified.
