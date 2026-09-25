# 1-menubar-fleet-patch-design

**Status:** waiting — parked · design gate
**Goal:** a proposal for the fleet-patch concept and its menu-bar indicator,
for Bob to ratify.

## Decide

- **Definition** of "the fleet patch" (see parent) — defined once, shared with
  `58` and `asset-fleet-distribution`.
- **Indicator:** placement in the header (`dashboard/static/index.html`),
  content (name + fingerprint tail + convergence), states (converged / drifting
  / unknown / offline), terse copy.
- **Actionable or display-only;** if actionable, the path and confirmation.
- **State plumbing** to the header via `dashboard.js` / `ws.js`.
- simfleet parity + a Playwright guard.

## Deliver

`decisions.md`; implementation stitch(es) from the ratified design; update the
parent.
