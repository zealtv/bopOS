# 1-menubar-fleet-patch-design

Design the fleet-patch global-state concept and its menu-bar indicator. Written
proposal, **Bob ratifies**, tie with `decisions.md`.

## Decide

- **Definition of "the fleet patch."** New first-class fleet target, or a
  projection of per-node desired-patch state? Coordinate with
  `29-fleet-patch-sync-hang` and `asset-fleet-distribution` so it's defined once.
- **Menu-bar indicator:** placement in `dashboard/static/index.html`'s top
  chrome, what it displays (name + fingerprint tail + convergence summary),
  states (all-converged / drifting / unknown / offline), and terse copy.
- **Actionable or display-only** from the menu bar; if actionable, the OSC/admin
  path and confirmation model.
- **State plumbing:** how fleet-patch state is computed server-side and reaches
  the menu bar (`dashboard.js` / `ws.js`), without coupling to a single tab.
- Simulator parity + a Playwright guard for the indicator.

## Deliverable

`decisions.md` here; child implementation stitch(es) from the ratified design;
update the parent.
