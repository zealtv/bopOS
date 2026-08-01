# 06-control-panel-reflow-and-editor

Fix how the control panel reflows, then make the patch editor use it.

## Reflow (Bob, 2026-07-30)

- A parameter row is **atomic**: `[value box 58px][name-in-slider flex][∿ 18px]`
  never wraps as the parent narrows. The slider absorbs the loss.
- The generator drawer **never reflows**. Its fixed width sets the panel's
  `min-width`; below that the panel scrolls rather than rearranges.
- `design-language.md` §7 currently says "the row may wrap before boxes
  shrink" — that sentence is the defect. Update the ratified doc as part of
  this stitch and note the supersession.
- Confirm the resulting minimum width is reasonable on a phone. If it is not,
  that is a finding for Bob, not a licence to reflow the drawer.

## Patch editor adopts the shared panel

`dashboard.js:898-927` (`editorControl` / `editorParamTree`) hand-rolls its own
parameter rows — a `<label><span>name</span><output><input type=range>` float
row, a `.toggle` checkbox, a text variant, and its own hierarchy accordion. It
has no generator drawer, no mixed-state encoding, no marker line, no event
rows. `dashboard.js:1362` is honest about why: *"the patch editor keeps its own
parameter tree (it drives one audition engine and predates the shared surface),
but its PRESET row is the shared, ratified one."*

Bob, 2026-07-30: *"anywhere there is a control for a patch that should present
the same control panel with the same UI and the same features."*

`editorSurface` already exists (`dashboard.js:1365`) and is used for the preset
row. Widen it to render the parameter tree. Two things to resolve honestly:

- The editor targets **one audition engine**, not a seat aggregate. Mixed-state
  encoding has no meaning there; make the single-member case render solid
  rather than inventing an aggregate.
- The editor's `dashboard` badge on promoted params has no home in the panel
  grammar. Decide where it goes (or that it goes away — the manifest
  `dashboard:` flag now gates only the facilitator view).

Verify: the editor journeys launch simfleet with `--sim-no-engine` and
`--sim-audio-backend none`, so this is testable headlessly
(`tests/verify_device_control_modes.py` is the template). Real PD/GUI behaviour
stays a hardware adoption check — say so, do not claim it verified.

## Added 2026-07-30 (Bob's tab-by-tab review) — ground and card

Bob, reviewing the shipped Control tab: *"control looks broken because there is
an inner panel with a pink background, so the control panel is swimming in empty
space."*

This is now **design-language §12** (ground and card): `--bg` is the workspace
ground, visible only as gutter between cards, and nothing but the page may set
`background:var(--bg)`.

The direct cause is `#dashboard-live-view{background:var(--bg)}` in `style.css`
— the Control-tab iframe is painted the ground colour *and* given a border and
radius, so it reads as a bordered pink box with a small card floating inside it.
Retiring that iframe belongs to `08`, but this stitch owns what replaces it:
when `ControlSurface` hosts in the parent document, the panel must land **on a
card**, not on the ground. Do not carry `background:var(--bg)` onto the new host
element.

Check the same thing for the patch editor when it adopts the shared panel: a
bordered region with a transparent background is the specific mistake §12 names.
