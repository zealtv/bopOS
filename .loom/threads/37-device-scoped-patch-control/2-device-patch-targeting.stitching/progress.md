# progress — 2-device-patch-targeting

## Bite 1 DONE (2026-07-24): per-device desired-patch foundation + resolution

Data model + effective-desired resolution + roster fields, fully unit-tested.
Deliberately **not** wired to a convergence path or UI yet (no way to *set* an
override from the client), so behavior is unchanged in practice until bite 2 —
the honest clean slice, no half-feature that shows "pinned" on a device that
never switches.

**Changed:**
- `dashboard/device_aliases.py`
  - `clean_desired_patch(value)` — validates `{name, fingerprint}`, lenient
    (bad → None, never invalidates the registry; live catalog re-resolves).
  - `clean_registry` preserves a valid `desired_patch` per entry (whitelist).
  - `set_custom` copies an existing pin through an alias rename (was dropping it).
- `dashboard/state.py` — `device_patch_for(uid)`, `set_device_patch_override(uid,
  name, fingerprint=None)`, `clear_device_patch_override(uid)`; persist in the
  durable UID registry entry (`desired_patch` key), save-with-rollback, mirroring
  `set_device_enabled`. Rides `durable()` via the whole-registry copy.
- `dashboard/server.py`
  - `device_desired_patch(device, fleet_desired)` — pin (re-resolved fingerprint
    from live catalog) else fleet default; virtual devices always follow fleet.
  - `public_device` computes `patch_badge` against the **effective** desired and
    publishes `patch_pinned` (bool), `pinned_patch` (name|None), `desired_patch`.
- `tests/test_device_patch_override.py` — 7 tests (clean/round-trip/persist/
  guards), green. `test_device_enabled.py` still green; `server` imports.

## Bite 2 — NEXT (not started)

1. **`set_device_patch` / `clear_device_patch` (`follow fleet`) WS commands.**
   Persist via the state methods above, then converge just that node. The hard
   part: `converge_fleet_patch` takes `(name, fingerprint, targets, base_urls,
   generation)` and does NOT read the global `fleet_patch` internally, so a
   singleton `targets={uid}` call is close — BUT `fleet_generation` /
   `supersede_fleet_operation` are global and reset every device's
   `patch_switch`. A per-device op needs its own generation/task tracking so a
   fleet deploy and a device pin don't cancel each other. Design this before
   coding. Register both in the WS allow-lists (`server.py:269`, `:281`).
2. **Patches-tab target picker** (fleet OR one device) — `renderFleetPatch`
   (`dashboard.js:463`) + `index.html:76-80`. Fleet path stays `set_fleet_patch`.
3. **Roster "pinned" marker** from `patch_pinned`/`pinned_patch` — a separate
   axis from `patchBadge` (`dashboard.js:459`); pin affordance + "follow fleet"
   clear. Rollup count feeds thread 34's deferred chip (chip NOT built here).
4. **simfleet parity** + Playwright (per-device deploy, pinned marker, follow
   fleet) → `tests/` by surface.
