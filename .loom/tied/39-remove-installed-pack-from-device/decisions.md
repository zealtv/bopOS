# 39-remove-installed-pack-from-device — decisions & findings

## What shipped

- **Catalog-row Remove** (`assetCatalogRow`, `dashboard/static/js/dashboard.js`):
  installed catalog packs (state `current`/`stale`/`unknown`) now render a
  `danger` **Remove** button beside any primary send/update action, matching the
  extra-row control. Absent rows show only **Send**; a `current` row that
  previously read "No action needed" now offers Remove.
- **Verb reuse:** no new server/OSC path. `drop_distribution` +
  `dropassets` already remove an asset by name regardless of whether it is a
  host-catalog slot or a device-only extra; the click handler, the active-slot
  guard (`confirmAssetAction`), and the observed-inventory feedback
  (`resolveAssetFeedback`) were already generic over `action==="remove"`.
- **Guard: warn, not block** (matches the existing extra-row choice, Bob's call
  left open). Removing a pack the device's active patch still declares
  (`active_asset_slots`) throws the existing "can immediately break the running
  patch … safer sequence: side-by-side generation, switch, then remove" confirm.
  Blocking was rejected: an operator sometimes genuinely needs to clear an
  active slot, and the warning already states the safe sequence.

## Bug uncovered and fixed (server)

`dashboard/server.py` `handle_ws`: the `set_param` branch did
`identity = declaration["identity"]`, which made `identity` a **function-local**
across all of `handle_ws`. The `drop_distribution` branch calls
`identity.valid_asset_slot(name)` (the module import) — so **every** asset drop
(catalog *and* the older extra-row Remove) raised
`UnboundLocalError: identity` and silently dropped nothing. This regressed after
`11b` was tied, when a later stitch added the `identity =` assignment; the tied
`11b` guard was never re-run, so it went uncaught — a concrete instance of the
tied-guard-rot problem (thread 27).

Fix: renamed the local to `param_identity` (5 uses) with a comment naming the
shadowing hazard. `replay_live_params_for_seat` and `live_param_declaration`
also bind a local `identity` but never touch the module in-scope, so they were
left alone.

## Verification

`verify_remove_installed_pack.py` (real dashboard + simfleet, headless
Chromium): absent→Send-only, installed non-active row surfaces Remove and
converges to absent (plain confirm, no active warning), only the selected
device is touched, and an active catalog slot's Remove throws the
break-the-running-patch warning. All pass.

**Hardware-verified (Bob, 2026-07-24, Ciro Toast).** From the Asset tab: added
then removed two catalog asset packs, and removed a device-only (extra) pack —
all successful. File addition and removal confirmed on the node over SSH. This
also exercises the `identity`-shadowing server fix on real hardware (the drop
path that was silently no-op'ing before). Adoption check closed.
