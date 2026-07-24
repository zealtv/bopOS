# 2-device-patch-targeting

Implement the ratified first bite of device-scoped patch control. Authority:
`../1-device-patch-control-design*/decisions.md` (Bob-ratified 2026-07-24) and
`proposal-first-bite.md` in the same design stitch.

## Scope (exactly this — no shared-surface restructure, no Control rename)

1. **Per-node desired-patch override (data model).**
   - Persist per-device overrides in the durable UID registry alongside
     alias/enabled state (survives restart, keyed by exact UID; mirror
     `device_enabled_for` in `state.py`).
   - Effective desired patch for a device = override if set, else the fleet
     patch. Resolve per device in `public_device`; `patch_badge` measures
     convergence against the *effective* target (convergence semantics
     unchanged). See `dashboard/server.py:1405` (`live_fleet_patch`),
     `:1414` (`public_device`), `:1439` (`patch_badge` call).

2. **`set_device_patch` WS command** `{uid, patch, confirmed}` — reuses
   `converge_fleet_patch` (`dashboard/server.py:1716`) with a **singleton target
   set**; do not fork the convergence machinery. A "follow fleet" action clears
   the override (node tracks the fleet default again). Register in the WS command
   allow-lists (`server.py:269`, `:281`).

3. **Patches-tab target picker (first pass).** In the Fleet-patch panel
   (`dashboard/static/index.html:76-80`, `renderFleetPatch` at
   `dashboard.js:463`): choose patch → choose target = whole fleet *or* one
   device. Fleet path stays `set_fleet_patch`.

4. **Roster "pinned" marker.** A device with an override reads as **pinned**
   (pin affordance, tooltip naming the pinned patch + "follow fleet" clear),
   a **separate axis** from the convergence badge — do not overload
   `patchBadge`/`PATCH_BADGE_LABELS` (`dashboard.js:459`). Fleet-patch
   convergence rollup data should include a pinned count (feeds thread 34's
   deferred menu-bar chip; the chip itself is NOT built here).

5. **Simulator + tests.**
   - `tools/simfleet.py`: honor a per-node override so a targeted device
     converges independently while the rest hold the fleet patch.
   - Playwright: per-device deploy, roster pinned marker on the targeted node +
     `current` on the rest, "follow fleet" clears it. Put assertions in `tests/`
     by code surface (durable-contract policy), NOT a new tied guard.

## Test rig

Finn Jet (fleet node) + Ciro Toast (standalone) — exercise per-device switch and
pinned display across both; see `finn-ciro-test-rig` memory. Software/browser
gates pass in CI; real-Pi behavior remains a hardware adoption check.

## Deferred to parent / other threads (do NOT build here)

Shared control-surface component, Control-tab rename, per-device live-control
panel, "Set patch…" Device-tab hand-off, presets (41), precision entry (40),
generator editing (`feature-backlog/38`), the menu-bar chip (`feature-backlog/34`).
