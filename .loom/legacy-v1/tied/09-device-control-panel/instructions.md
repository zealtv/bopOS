# 09-device-control-panel

Put live controls for one device on the Device tab, and fix the panel order Bob
asked for while the area is open.

**Authority:** `.loom/tied/5-live-control-placement-design/decisions.md` (Bob,
2026-07-25).

**Depends on:** `07-control-surface-component`.

## Ratified

1. **Device-tab order becomes:** patch diagnostics → **device actions** (moved
   up) → **device control** (the new panel). Bob: "move the device actions up
   directly below the diagnostics while you a here, device control sits below
   actions."
2. **Collapsed by default**, collapse state remembered (existing panel-persistence
   pattern).
3. **Offline: disabled, showing last values.** Never hidden. Reuse the durable
   offline/unbound value behaviour already ratified in stage 7 — do not add an
   offline branch of your own.
4. **One code path.** Same `ControlSurface`; only the send target differs.

## The schema problem — solve this deliberately

The panel renders the device's **effective** patch: its pin if pinned, else the
fleet patch. But `public_state()` publishes exactly one fleet-wide
`live_controls` schema, built from `params_patch`
(`dashboard/server.py:1516`, `live_control_manifest()` at 1383, which hardcodes
`self.state.data["params_patch"]`).

A **pinned** device may be running a different patch with different promoted
params, so the fleet schema is the wrong one for it. The clean seam is to
parameterise `live_control_manifest(patch_name=None)` and publish per-device
declarations for pinned devices. Decide how they reach the client (per-device
field on the public device vs a keyed map) and record it in `decisions.md`.

## Scope on the wire

Add `scope: "device"` carrying a uid. On the wire it resolves to the device's
**seat** selector — pinning already requires a seat binding (OSC v1.5 targets
content by seat), so there is always one. Extend `live_param_target()` for it.
Keep the resolution honest and commented: the device scope is a *presentation*
scope over a seat-selector send.

An **unbound** device has no target — render the panel disabled with a short
note pointing at the seat requirement, consistent with what
`11-set-patch-handoff` offers.

## Consequence

This **retires** the Seats-detail vertical-overflow complaint rather than
patching it. Check whether anything in the Seats detail should now be removed as
redundant; if so, say so in `decisions.md` rather than doing it silently.

## Verification

`tests/` (thread-27 policy). Cover: panel order on the Device tab; collapsed by
default and remembered; an offline device shows last values disabled; a write
from the panel reaches only that device; a **pinned** device renders its own
patch's params, not the fleet's.

**Trap (CLAUDE.md gotcha 12):** scope roster clicks to `#device-roster` — seat
rows carry `data-uid` too.
