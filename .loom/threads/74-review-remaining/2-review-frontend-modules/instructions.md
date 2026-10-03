# 2-review-frontend-modules

**Status:** ready · after `65` and `68` remove their UI is better
**Goal:** review the frontend modules the first pass only spot-checked.

Scope: `control-surface.js` (1,264 lines), `control-column.js`, `spatial.js`,
`monitor.js`, `target-picker.js`, `param-generator.js`, `ws.js`, and the CSS
(`control-panel.css` is 1,705 lines).

Look for: escaping of device-supplied strings in `innerHTML`, listeners leaked
across re-renders, render-on-every-heartbeat costs, dead CSS, and rules from
`glean:dashboard-vocabulary` (component CSS ownership, colour meanings). Deliver
as the parent says. `dashboard.js` itself is `69/5`.
