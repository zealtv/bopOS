# Decisions — 43-live-param-checkbox-nosend

## Root cause (resolves the handoff's "paradox")

The server was never wrong, and the payload the *code appeared to send* was
fine — replaying `{scope:"all", name:"green-button", value:1}` by hand against
the live server (PID 576, same state) was **accepted**. Capturing the real
browser frame showed the actual defect:

```json
{"type":"set_live_param","data":{"scope":"all","name":"green-button",
 "value":{"isTrusted":true}}}
```

The **DOM Event object** was going to the wire as the value. Thread
`40-precision-param-input` (commit `a978cd9`) changed the facilitator's
`send()` to `send(override)` so the precision field could pass an exact typed
value — but the handlers stayed bound as `input.onchange = send` /
`input.onpointerup = send`, so the browser's Event argument landed in
`override`, JSON-serialized as `{"isTrusted":true}`, and
`clean_editor_value` (dict is neither str nor number) correctly returned
None → "That live parameter or target is unavailable."

- **Checkboxes**: only bound via `onchange` → every toggle rejected. Fully
  broken since `a978cd9`.
- **Sliders**: the throttled `oninput` → `send()` (zero-arg) delivered the
  value first, so they *appeared* to work; their `onchange`/`onpointerup`
  commits were silently rejected too (masked, pre-Fix-#2, by the missing
  error handler).

## Fix

`dashboard/static/js/facilitator.js`: wrap the three handler bindings so the
Event never reaches `override` — `input.onchange = () => send()`,
`input.onpointerup = () => send()` (range branch) and
`input.onchange = () => send()` (checkbox/text branch). The precision-field
callback keeps passing its explicit value.

Audited the same pattern elsewhere: `facilitator.js` master slider and
`dashboard.js:1281` bind `= send` too, but those `send` closures take no
parameters, so the Event argument is harmless. No other `override`-style
callbacks exist.

## Inherited fixes kept (per handoff)

1. Broadened pointerdown matcher to
   `input[type="checkbox"][data-live-param]` so plain live checkboxes set
   `interacting` and survive heartbeat `renderCards()` during the gesture.
2. New facilitator `ws.on("error")` handler — server rejections now surface
   as alerts instead of being silently buffered.

## Test

Durable verify at `tests/verify_live_param_checkbox.py` (per the 2026-07-23
tests-not-tied-guards ruling): real dashboard + simfleet at 0.2 s heartbeat
cadence, clicks the All-card checkbox, asserts the numeric wire write
(`p/gate=1`/`=0` in the fleet log), the on-disk `installation.json` seat-param
update, checked-state survival across re-renders, no rejection alert, and the
slider change-commit path. Confirmed it fails (5 checks, with the exact field
alert) when the fix is reverted.
