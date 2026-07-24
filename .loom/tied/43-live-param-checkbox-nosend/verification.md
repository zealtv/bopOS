# Verification — 43-live-param-checkbox-nosend

Date: 2026-07-24. Venv: `~/.venvs/bopos`.

## Live repro + fix confirmation (real running dashboard, PID 576, :8080)

1. **Direct ws replay** of `{scope:"all", name:"green-button", value:1}` →
   ACCEPTED (state broadcast, seats updated). Proved the server path healthy
   and pointed at the client payload.
2. **Instrumented real browser click** (WebSocket.prototype.send hook) on the
   All-Seats green-button checkbox → captured
   `value: {"isTrusted":true}` + the "unavailable" alert. Root cause found.
3. **After fix + hard reload:** click sends `value: 0` (numeric), no alert,
   state persists, checkbox stable across heartbeat re-renders for 4 s.
   green-button left at 0 (its pre-session value; the transient
   `green-button 1` from step 1 was reverted by this click).

## Durable test (`tests/verify_live_param_checkbox.py`)

- With fix: **10/10 PASS**.
- With fix temporarily reverted: **5 FAIL** — missing `p/gate=1` wire write,
  no state persistence, checkbox revert, and the exact field alert
  "That live parameter or target is unavailable." (three occurrences).
  The test catches the regression.
- `tests/verify_precision_param_input.py` exercises the precision-field
  `send(value)` path this fix must not break; its coverage is unchanged by
  the wrap (explicit-argument calls unaffected).

## Not verified here

- Audible/hardware behaviour on Ciro (fire-button PD patch reacting to the
  toggle). Wire + node routing were already proven healthy in the 42 session's
  evidence chain; the defect was purely browser-side payload construction.
