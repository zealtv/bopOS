# Decisions — identity and fingerprint promotion

## Promoted assertions

| Living surface | Durable properties | Archived context inspected |
|---|---|---|
| `tests/test_identity_fingerprint.py` | node UID resolution prefers a pinned token, then supplied runtime identity, then discovered hardware identity, with an opaque boot fallback | `hb-identity`; `assign-persistence` |
| `tests/test_identity_fingerprint.py` | persisted assignment and explicit unassignment outrank the seed file; assignment is exact-UID full state; unassignment leaves a `-1` tombstone and clears routing identity | `assign-persistence`; `d8-1-seat-model`; seat identity guards |
| `tests/test_identity_fingerprint.py` | canonical directory identity ignores hidden, symlinked, and in-flight content; changed visible bytes invalidate identity; cold or changed cached inventories report unknown until warmed | `fp-1-identity-module`; `patch-fingerprint-warm` |
| `tests/test_identity_fingerprint.py` | dashboard catalog, node inventory, and simfleet compute the same patch and asset fingerprint for the same bytes | `fp-1-identity-module`; `fp-2-fleet-state` |
| `tests/test_identity_fingerprint.py` | patch drift is derived, non-mutating state; additive patch/asset inventory facts are tolerated; absent or malformed identities degrade to unknown rather than rejecting an otherwise usable entry | `fp-2-fleet-state`; asset inventory context |

The tests exercise production `bopos.py`, `identity.py`, dashboard state/catalog
and OSC ingestion, plus simfleet helpers. They assert precedence, identity
equality, and classification properties rather than complete wire verb lists
or old contract-version literals.

## Existing living coverage retained

- `tests/test_device_patch_override.py` owns cleaning and durable round-trip of
  per-device desired patch pins.
- `tests/test_asset_slot_context.py` owns canonical asset-slot discovery and
  engine run-context ordering.
- `tests/test_node_fetch_dispatch.py` already proves that assignment does not
  mutate the physical device hostname.
- `tests/test_fetcher.py` owns verified byte convergence and pruning.
- `tests/verify_device_patch_targeting.py` owns the browser-level pin,
  fleet-follow, and convergence journey.

Those contracts were audited and not duplicated wholesale.

## Product correction

The new malformed-inventory case exposed a logger-shadowing defect in
`OSCBridge.handle`: the `/os/log-config` branch assigned a local named `log`,
so later warning paths could not access the module logger and crashed with
`UnboundLocalError`. Renaming that local to `log_config` restores the already
ratified behavior: malformed asset facts are quarantined and represented as
unknown without dropping the rest of the inventory.

## Superseded or deliberately omitted assertions

- Assignment no longer renames the device hostname; archived assertions that
  expected this are superseded by the physical Device versus Seat boundary.
- Exact dashboard copy, badge markup, complete verb lists, private cache
  dictionaries, and obsolete contract-version literals were not promoted.
- The archived full simfleet fleet-switch journey remains integration
  evidence. Living fetch and targeting tests own convergence mechanics; this
  stitch promotes only shared identity and derived drift semantics.
