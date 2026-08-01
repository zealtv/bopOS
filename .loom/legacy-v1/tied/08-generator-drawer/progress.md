# 08-generator-drawer — done

Every numeric row on the shared control surface now carries a `value ▸ gen`
switch that opens an inline drawer hosting the ratified generator builder, with
stop inside the drawer.

## What shipped

- **`dashboard/static/js/param-generator.js`** — the automation-2 builder,
  extracted from `show.js`: `fields`, `preview`, `compile`, `blank`,
  `segmentRow`, `unitOptions`. Markup, class names and data-attributes carried
  over unchanged so the existing CSS keeps applying to both hosts.
- **`show.js` delegates to it.** `renderParamPreview`,
  `renderParamGeneratorFields`, `renderUnitOptions`, `renderParamSegment` and
  `compileParamEditor` are now thin wrappers; the local `inputNumber` /
  `durationString` / `paramValueAttrs` helpers are gone. `compile` takes the
  mode as an argument rather than scraping a fixed element id, which is the only
  change the extraction needed.
- **`control-surface.js`** — the switch, the drawer, and their bindings.
- **`server.py`** — the `set_live_automation` ws verb (rationale in
  `decisions.md`).
- **CSS** — drawer chrome in `style.css`; drawer chrome *plus* the
  `show-param-*` field styles in `facilitator.css`, because that page does not
  load `style.css` and the builder markup is now shared.

## Verification

- **`tests/verify_generator_drawer.py` — new, 38/38 green.** Runs its whole
  scenario twice, once with agreeing seats and once with disagreeing ones. Pins
  each ratified ruling: the switch is exactly two states and appears on numeric
  rows only; the drawer is an inline **sibling** of its row (not a popover);
  **stop is inside the drawer** and adds no third switch state; and — the one
  that matters most — a **mixed aggregate is not disabled**, with a committed
  generator recorded for every member seat.
  It also pins the wire end to end: after Apply the node's density **ticks**
  with changing values and simfleet logs no grammar error, and after Stop the
  ticking halts and the recorded automation clears.
- `tests/verify_control_surface_component.py` — 11/11 (normalizes the new
  `data-gen-key`, which is scope-derived for the same reason the scope
  attributes are).
- `tests/verify_live_param_checkbox.py` — 10/10.
- `tests/verify_precision_param_input.py` — 13/13.
- Tied guards run from copies, then deleted: **`automation-2-show-builder-gui`
  9/9** (the Show inspector still compiles identical wire args through the
  extracted builder — the check that the extraction is faithful) and
  **`automation-5-waveform-marker` 19/19**.

## Wire assertion worth knowing about

The first draft of the verifier looked for the generator command echoed in the
fleet log and failed. That was the *test* being wrong: simfleet does not echo
the command, it parses the §3.2 message, runs a real generator engine and logs
the **scalar ticks** the engine emits. Asserting on a stream of changing ticks
(and on the absence of a grammar error) is a stronger claim than an echo would
have been, so the check was rewritten rather than the code.

## Deferred, deliberately

`value` mode in the drawer is not offered — the row's own slider and precision
field are the value affordance, so the drawer's kind list is `fade / loop / lfo`
with stop as an action. `blank()` still knows the `value` shape because
`ParamGenerator` also serves the Show inspector, which does offer it.
