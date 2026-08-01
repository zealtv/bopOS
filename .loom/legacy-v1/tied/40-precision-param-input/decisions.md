# 40-precision-param-input — decisions & findings

## What shipped

Precision typed entry on numeric parameter controls, as a click-to-type layer
on the existing slider readouts (the established click-to-edit idiom — see
`18-show-chrome-density/04`). Sliders stay a gesture tool; exact numbers now have
a keyboard path.

- **Shared helper** `dashboard/static/js/precision-field.js` →
  `window.PrecisionField.attach(output, spec, commit, guard)`. Loaded on both
  `facilitator.html` and `index.html`. Clicking (or focusing + Enter/Space) an
  `<output data-precise>` swaps in a `<input type="number">`. On commit the typed
  value is **clamped** to the control's min/max and **rounded** to the wire's real
  precision — integers for an integer control, otherwise **6 significant figures**
  (`toPrecision(6)`), honouring the house =<6-sig-fig / 32-bit-PD-float rule.
  Enter/blur commit, Escape reverts, and the value is handed to `commit(value)`.
  The helper is decoupled from the range element (callers pass a plain spec) so a
  control shown in different units than it sends can convert inside `commit`.
- **Facilitator live surface** (`facilitator.js`): plain numeric readouts (not
  mixed/automated) gain `data-precise`; the field commits through the *same*
  `send()` path as the slider, with an `override` argument so the exact value
  **bypasses the range's coarse `step`** (a range's `.value` snaps to step and
  would destroy precision). The `interacting` flag is the re-render guard while a
  field is live. Mixed/automation readouts keep a static display so takeover
  semantics are unchanged.
- **Patch-editor control panel** (`dashboard.js`): the same on `data-editor-param`
  numeric rows (commit → `set_editor_param`) and the **master** slider, which is a
  0..1 level shown as integer percent — precision entry drives it in whole percent
  to match the readout and the slider's 1% step.
- **Show-tab inspector** — verify-only per the brief. `show.js` already emits
  `type="number" step="any"` (via `paramValueAttrs`) for float params; **no change
  made**. Typed floats reach the wire through the same `osc.set_param` path the
  facilitator phase proves preserves full precision, so they survive by the same
  mechanism.

## Small UX call (implementer's, per the brief)

Chose **click-to-type on the readout** over an always-visible second field: less
visual weight per row, and it matches the existing click-to-edit title idiom.
Values **clamp** (not reject) to bounds, consistent with slider behaviour; the
server's `clean_editor_value` rejects out-of-range, so the client clamp keeps
every sent value acceptable. Master precision is whole-percent (its readout and
step are already 1%); sub-percent precision there would imply more than the
control shows.

## Verification

`tests/verify_precision_param_input.py` (real dashboard + simfleet, headless
Chromium). Homed in `tests/` rather than a tied stitch guard because
`precision-field.js` is a genuinely shared surface used by both pages — the
durable-tests direction (Bob, 2026-07-23; thread 27). Checks:

- **Phase A — facilitator, real wire capture** (engine alive; the simfleet fleet
  log is the OSC capture, `p/<name>=<value>` via `%g`): a typed `0.137913`
  reaches the wire at full precision and round-trips into every scoped seat's UI
  state; an over-max `2.5` clamps to `1` on the wire; an integer control rounds
  `6.7 -> 7`; Escape reverts and sends nothing; `PrecisionField.round` honours 6
  sig figs and integer rounding.
- **Phase B — dashboard page**: helper is loaded; `editorControl` renders precise
  readouts for numeric params but plain checkbox/text for toggles/strings; and a
  DOM-contract probe drives the shared helper (click → type over-max → Enter
  clamps to bound; Escape → no commit).

**Editor live-mode note:** the patch-editor panel only stays active headlessly
with a faked PD engine peer (as `tests/verify_device_control_modes.py` builds) —
without one, `installation.editor.active` flips false and the panel empties.
Standing that up purely to exercise the editor's 3-line commit callback (which
drives the identical shared helper Phase A proves against the real wire) was
judged disproportionate; the editor is covered by its markup contract + the
shared-helper DOM probe + Phase A's end-to-end proof of the helper.

Real Pi/PD audible behaviour remains a hardware adoption check.
