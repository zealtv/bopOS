# 40-precision-param-input

Precision float entry on every parameter control. From Bob's 2026-07-24
patching-session braindump (lore `2026-07-24-patching-session-braindump`):
"the slide is great, but we also need to do precision float input wherever
we're controlling a parameter." Sequencing and deliberate composition need
exact numbers; sliders alone are a gesture tool.

**No design gate** — this is a property of the existing parameter control,
not new IA. Small UX calls (click-to-type vs. always-visible field) are the
implementer's, matching existing dashboard idiom (click-to-edit titles are
the established pattern — see the tied `18-show-chrome-density/04` unified
click-to-edit title work).

## Scope (surveyed 2026-07-24 — anchors verified then)

Wherever a numeric `/p/*` parameter is controlled with a slider or drag:

- **Live-control surface** — the promoted-control range input at
  `dashboard/static/js/facilitator.js:221` (`live-param-range-wrap`,
  `<output>` + `<input type="range">`); its send path is ~`:498-511`.
  This is the All & Groups / Seats surface. (The Device-tab panel arrives
  with thread 37 — it will inherit whatever this stitch builds; coordinate,
  don't duplicate.)
- **Patch-editor control panel** — `dashboard/static/js/dashboard.js:671`
  (`data-editor-param` range row) and the master slider at `:777`; send
  path `:779-780`.
- **Show-tab inspector** — already uses typed `<input type="number">`
  fields (`dashboard/static/js/show.js:745` param value, `:752-753` LFO
  min/max, via `paramValueAttrs` at `:737` which already emits
  `step="any"` for floats). **Verify-only here**: confirm typed floats
  survive to the wire with full precision; fix only if they don't.

The pattern to build: the existing `<output>` readout becomes (or gains)
click-to-type — an inline editable value next to the slider, in the
established click-to-edit idiom (see the tied `18-show-chrome-density/04`
title pattern). Both range and typed input write through the same send
path so fade/mixed/automation attrs (`data-mixed`, fade attrs at
facilitator.js:221) keep working.

Behavior:

- Typed values validate against the manifest `min`/`max`; clamp or reject
  consistently with however the slider bounds behave.
- Preserve full typed precision on the wire (PD floats are 32-bit — the
  house ≤6-significant-figures rule still applies; don't imply more
  precision than the wire carries).
- Keyboard-friendly: commit on Enter, revert on Escape, don't steal focus
  from show playback shortcuts.

## Verify

Headless Playwright `verify_*.py` against simfleet per the standard recipe
(copy the newest tied template): type a precise value into each surface in
scope, assert the exact value arrives on the wire (sim OSC capture) and
round-trips into the UI state.
