# decisions — first bite of device-scoped patch control

Ratified by Bob, 2026-07-24. Full rationale in `proposal-first-bite.md`. This
covers only the **first clean bite**; the shared control-surface restructure,
Control-tab rename, per-device live-control panel, and preset affordances remain
open in the parent thread.

## Ratified

1. **Data model.** Introduce a **per-node desired-patch override**. Effective
   desired patch for a device = its override if set, else the fleet patch.
   `public_device`/`patch_badge` compute convergence against the *effective*
   target per node. The fleet patch stays a bulk-set/default over per-node
   desired patch (confirms the parent's framing).

2. **Persistence — durable UID registry.** Per-device overrides persist in the
   durable UID registry alongside alias/enabled state — survive dashboard
   restart, keyed by exact UID, same discipline as `device_enabled_for`.

3. **Target picker (Patches page), first pass.** Choose a patch → choose a
   target = whole fleet *or* one device. Deploy-to-fleet stays `set_fleet_patch`;
   new WS command `set_device_patch {uid, patch, confirmed}` reuses
   `converge_fleet_patch` with a **singleton target set**. A "follow fleet"
   action clears the override so the node tracks the default again.

4. **Roster badge — "pinned".** Deliberate per-device targeting reads as
   **pinned** (pin affordance, tooltip naming the pinned patch + a "follow fleet"
   clear), kept as a **separate axis** from the existing convergence badge
   (`current`/`stale`/`switching`/`failed`…). The two axes are not overloaded
   into one badge.

5. **Fleet-patch mirror — data here, chip deferred to 34.** Land the drift +
   fleet-patch convergence-rollup **data** in this bite; the persistent menu-bar
   convergence **chip** renders as part of `feature-backlog/34-fleet-patch-global-state`
   (its explicit purpose). Drift + the fleet-patch definition are defined **here**
   so 34 and `29`/`asset-fleet-distribution` share one definition.

6. **Generator editing PARKED** to `feature-backlog/38-generator-editing-on-surface`.

## Deferred (still parent-thread, not this bite)

Shared control-surface component, Control-tab rename, Device-tab per-device
live-control panel, "Set patch…" Device-tab hand-off, preset affordances
(thread 41), precision float entry (thread 40).

## Child implementation stitch

`2-device-patch-targeting` — implement items 1–5 server + client + simfleet +
`tests/` coverage.
