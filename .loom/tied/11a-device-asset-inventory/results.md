# Results — device asset inventory

## Outcome

- Revised the additive OSC contract to v1.6 with
  `/<id>/os/assets -> /os/assets <json>` and an explicit unknown-versus-empty
  distinction.
- Added a node-side atomic `.hashcache.json`, strict stat-signature validation,
  garbage collection, low-priority/throttled background warming, and a query
  path that never hashes file content.
- Seeded verified per-file hashes at successful asset fetch completion so the
  first post-fetch fingerprint needs only a stat walk.
- Added real-node and simulator inventory replies with canonical fingerprints,
  fresh file/byte counts, fetch/refetch updates, and drop removal.
- Added dashboard observation on discovery, asset fetch receipt, and revision
  receipt; capped null-fingerprint backoff; observed-at markers; malformed-entry
  quarantine; and honest handling of older-node silence.

## Verification

- Focused non-browser verifier: **27/27 passed**. It covers cold-to-warm
  resolution, restart persistence, out-of-band edits, fetch seeding, no-hash
  query behavior, real wire shape, simulator snapshot/refetch/drop, dashboard
  observation, malformed entries, unknown versus empty, bounded retries, and
  all refresh edges.
- Python compilation passed for every changed Python file and the verifier.
- `git diff --check` passed.
- Existing group dashboard state/bridge suite: **6/6 passed**.
- Existing Seat identity state/server regression passed.
- Existing shared fingerprint verifier passed every identity/node/simulator
  assertion except its obsolete hard-coded expectation that the simulator
  advertise contract v1.4; v1.6 is the intended result.
- Two older distribution verifies retain unrelated stale expectations: one
  races queued progress against terminal fetch receipts, and one asserts UI
  copy/layout removed before this stitch. The fleet-state suite passed 25
  assertions before its retained legacy simulated-switch receipt failure.

## Unexercised surfaces

`bop000`, the installation LAN, SD-card cold-read timing, audio-engine load,
and the audible rig were not exercised. No `.pd` file changed.
