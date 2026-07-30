# Decisions

## Native input is the component

Numeric entry stays a native `input[type=number]`: it already provides the
universal click-to-type interaction and preserves every caller's keyboard,
validation and event behavior. `ValueBox` decorates static and dynamically
rendered inputs, then normalizes their committing `change` in capture phase so
existing handlers read the safe value without depending on the component.

When normalization changes a value, the component emits one `input` event
before the original change handler runs. This keeps input-backed drafts (the
manifest editor and generator drawers) at the same clamped, six-significant-
figure value as the DOM and eventual wire value.

`PrecisionField` keeps its plain display-unit spec and `commit` conversion. It
now delegates rounding and face decoration to `ValueBox`, so master percentage
and parameter readouts share the component without coupling it to a slider.

## Alignment and dimensions

All current numeric inputs use the 58px standard. There are no wider
exceptions. Three old Seats rules that silently widened numeric fields to 64,
80 or 88px were retired.

An explicit `integer` spec or `data-integer` wins; otherwise native `step="1"`
identifies an integer field. Generator parameter fields carry the declaration's
real kind explicitly. Event lead is also marked explicitly because its integer
step is 50 rather than 1. Floats align left and integers right.

The face lives in `css/value-box.css` because the main app and standalone
facilitator load different base stylesheets. Both documents load this one
component stylesheet and `js/value-box.js`.
