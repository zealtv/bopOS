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

## Bite 2 DONE (2026-07-25): actuation + UI + verification

Design checkpointed in `design-per-device-convergence.md`. All ratified items
1–5 landed and verified headlessly; only real-Pi/PD behaviour remains a hardware
adoption check.

**Server (`dashboard/server.py`):**
- `device_operations` / `device_generations` — a per-device convergence track.
- `converge_fleet_patch(..., is_current=None)` — the liveness token is now
  swappable; the fleet path is unchanged (default = fleet generation), the device
  path passes its own device-generation check, so the two never cross-cancel.
- `_supersede_device_operation(uid)` — per-device mirror of the fleet supersede,
  scoped to one uid.
- `converge_device_patch(uid, name, ws)` — reuses `converge_fleet_patch` with a
  singleton target set + the per-device token; rejects virtual/unbound.
- `set_device_patch` / `clear_device_patch` WS handlers (registered in both
  allow-lists). Clear = "follow fleet" → converge to the fleet default.
- **Fleet deploy respects pins:** `stage_and_converge` excludes pinned devices
  from the fleet target set; `supersede_fleet_operation` no longer wipes a
  pinned device's `patch_switch`. `retry_fleet_patch` retries a pin, not the
  fleet, for a pinned device.

**Client (`dashboard/static/js/dashboard.js`, `index.html`, `css/style.css`):**
- Target picker (`#patch-target`): whole fleet OR one online seat-bound device;
  the button relabels Deploy ↔ "Pin to device". Fleet path stays `set_fleet_patch`;
  device path sends `set_device_patch`.
- `pinnedMarker(d)` 📌 on seat + device rows — a separate axis from `patchBadge`,
  tooltip names the pinned patch. Diagnostics show the effective (pinned) desired
  and a "Follow fleet patch" button (`clear_device_patch`).
- Fleet-patch summary carries a pinned count (feeds thread 34's deferred chip).

**simfleet — NO CHANGE NEEDED.** It is protocol-reactive and already models
per-device `active_patch`/`patches` with per-selector dispatch (`admin_verb`,
`fetch`). A singleton-targeted convergence reaches only that device — the exact
path the pre-existing single-device fleet retry already used. Recorded so the
next reader doesn't hunt for a missing simulator edit.

**Verification:** `tests/verify_device_patch_targeting.py` (real dashboard +
simfleet + Playwright, homed in `tests/` per thread-27 policy). 14/14 green,
incl. the crucial property — **a whole-fleet deploy leaves an existing pin
intact and converges only the unpinned device** — plus independent per-device
convergence, the roster pin marker, durable-registry persistence across reload,
and follow-fleet clear. `tests/test_device_patch_override.py` (bite 1, 7) +
`test_device_enabled.py` still green.

Command (from repo root, venv `~/.venvs/bopos`):
`~/.venvs/bopos/bin/python tests/verify_device_patch_targeting.py`

## Scope reality carried forward (see design note + handoff)

OSC v1.5 targets content ops by seat, so **pinning requires the device to be
seat-bound + online** (`distribution_targets(uid)` yields nothing otherwise) —
including the "standalone" Ciro Toast (bind it to its own lone seat). Not a new
limitation (the fleet retry guard already says it); the truly-seatless-control
question belongs to the deferred set-patch-hand-off / shared-surface design.

## Hardware verification — PASSED (Bob, 2026-07-25)

Bob ran the Finn Jet + Ciro Toast sequence from
`.notes/handoff-2026-07-25-device-patch-autopilot.md` on the real rig and
reported it **successful**. That closes the hardware adoption check this stitch
left open: per-device pinning, independent convergence, and — the property the
whole bite turns on — **a whole-fleet deploy leaving an existing pin intact**
hold on real Pis with real JACK/PD restart timing, not just against the
simulator's 2 s stub.

Nothing to change in the implementation; recorded here so the tied stitch is
not read later as still awaiting hardware.
