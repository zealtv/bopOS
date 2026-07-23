# 34-fleet-patch-global-state

**FEATURE.** There is, in general, one **fleet patch** — the patch the whole
fleet is meant to be running. That's **global state** the Dashboard should show
globally, most likely **up in the menu bar**, so it's always visible regardless
of which tab you're on.

Bob, 2026-07-23: "In bopOS on the server dashboard, generally there'll be a patch
that is the fleet patch, and that's like a global state that we need to be aware
of globally on the dashboard. So that's probably something that needs to be up in
the menu bar."

## What this is really about

Today the Dashboard reasons about patches per-device (desired/reported patch
fingerprint per node) and through the Patch tab. Bob is naming a *fleet-level*
concept — "the fleet patch" as a single global intended state — and asking for a
persistent, always-on-screen indicator of it, in the app's top menu bar.

## Bob gate

Menu-bar / global-chrome UI is user-facing Dashboard design — Bob ratifies.
Design first (`1-menubar-fleet-patch-design`), then implement.

## Questions the design must answer

- **Is "the fleet patch" a new first-class concept, or a projection of existing
  state?** (e.g. "the patch all bound nodes are converging on", or an explicitly
  set fleet target.) This bears on `29-fleet-patch-sync-hang` and
  `asset-fleet-distribution` — a fleet-patch send is exactly what broke the fresh
  Pi. Settle whether this thread *defines* the fleet patch or merely *displays*
  an already-defined one.
- **What the menu-bar indicator shows:** the fleet patch name/fingerprint, and
  convergence at a glance (all nodes on it / N drifting / unknown).
- **Is it actionable from the menu bar** (set/send the fleet patch), or
  display-only with the action staying in the Patch tab?
- Where the menu bar lives in `dashboard/static/index.html` today and how global
  state reaches it (`dashboard/static/js/dashboard.js`, `ws.js`).

## Relation

Deeply tied to `29` (the fleet-patch send is the broken path), `32-multi-asset-
packs`, and `asset-fleet-distribution`. Coordinate — the fleet-patch *definition*
should be settled once and shared, not defined twice.
