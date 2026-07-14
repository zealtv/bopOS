# fp-2-fleet-state

Fleet-scoped desired state and badge derivation, per ratified fp-0 §1, §3-§5.
Needs fp-1 tied (badges compare fingerprints).

- `installation.json` gains `fleet_patch` `{name, fingerprint, staged_at,
  previous: {name, fingerprint}}`; venue snapshots carry it.
- **Delete the per-seat `patch` field** (Bob, Q1: "delete. simplicity is a
  guiding principle") — `dashboard/state.py:108,158-162`; loading old state
  files drops it silently. No dormant heterogeneity hooks.
- `simulation["patch"]` becomes a read-through to `fleet_patch.name`.
- Badge derivation per device, precedence: `unknown/last seen` (offline or
  unqueried — never current/mismatched) → `switching` (`patch_switch` in
  flight or `patch:` fetch queued/fetching) → `missing` → `mismatch` (active
  name ≠ desired) → `stale` (names match, fingerprint differs or
  unreported → `stale (unverified)`) → `current`. Derived, never stored as a
  verdict; surfaced over WS.
- **Set fleet patch** is one confirmation-gated operation (Bob, Q2):
  converge content (fetch to non-current online nodes, respecting the
  expired-tombstone rule, `dashboard/osc_bridge.py:506-517`) then switch
  (per-device `/id/os/patch`, progress via `patch_switch`//os/rev` as
  today). All-at-once, no staged waves. `Revert` re-stages `previous`
  through the same flow. `stale` retry is operator-triggered only (Q3).
- Verify browser-free against simfleet: stage→converge→switch happy path,
  offline node stays `unknown`, induced stale (host edit after send),
  retry, revert.
