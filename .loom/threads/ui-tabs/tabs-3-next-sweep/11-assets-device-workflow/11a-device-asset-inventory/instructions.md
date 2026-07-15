# 11a-device-asset-inventory

Give the dashboard durable, queryable knowledge of the asset slots installed on
one device. Current `/os/fetched` receipts only describe a transfer completed
during this dashboard session and cannot establish state after restart.

Design gate before implementation:

- Specify the smallest additive request/reply parallel to `/os/patches`, likely
  `/<id>/os/assets` → `/os/assets <json>`.
- Each installed top-level slot must report its operator-defined name and the
  canonical directory-manifest fingerprint shared with the host catalog.
- Define malformed-entry handling, compatibility with older nodes, query timing
  (connect, after fetch, after drop), and whether file/byte totals belong here
  or remain host-only. Do not absorb future bulk-transfer progress or free-space
  reporting into this seam without a demonstrated first-workflow need.
- Record the exact proposed OSC amendment in this stitch and return it to Bob if
  it differs materially from the shape above. Do not implement past an
  unratified wire decision.

After acceptance, implement the term in node, simfleet, dashboard bridge/state,
and `docs/OSC-CONTRACT.md`. Use `python/identity.py` so host and node fingerprints
are identical. Prove reconnect/restart observation, successful fetch refresh,
drop refresh, malformed payload quarantine, and older-node unknown state with a
focused non-browser verifier.

Reference:
`.lore/items/2026-07-15-asset-management-direction/content/decision.md`.
