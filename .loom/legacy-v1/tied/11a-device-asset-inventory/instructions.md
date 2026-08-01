# 11a-device-asset-inventory

Give the dashboard durable, queryable knowledge of the asset slots installed
on a device. Current `/os/fetched` receipts only describe a transfer completed
during this dashboard session and cannot establish state after a restart.

The wire shape and caching design below were worked through with Bob on
2026-07-15 (the session that folded the scale reference into the loom), so an
autonomous session may implement without a further design gate. If
implementation forces a **material** deviation from this shape, stop, record
the deviation here, mark the stitch `.waiting`, and surface it to Bob.

Reference: `.lore/items/2026-07-15-asset-management-direction/content/decision.md`
and `.lore/items/2026-07-15-asset-transfer-scale-reference/content/reference.md`.

## Wire term (additive; contract v1.6)

```text
/<id>/os/assets            → /os/assets <json>   (unicast, like /os/patches)
```

The JSON is a list of installed asset slots, mirroring the `/os/patches`
naming style:

```json
[ {"name": "belief-system-000", "fingerprint": "<64-hex or null>",
   "files": 412, "bytes": 1234567890} ]
```

- A slot is a top-level non-dot, non-symlink directory under
  `~/bopOS/assets/`. Empty list means "no slots"; **no reply means unknown**
  (older node) — consumers must never render silence as an empty inventory.
- `fingerprint` is the canonical directory-manifest sha256
  (`python/identity.py`, identical to the host catalog for the same bytes),
  or `null` while not yet known. **The reply path never hashes file
  contents** — see caching below. `files`/`bytes` come from the same
  walk-and-stat rules the manifest uses (dot-entries, symlinks, `.part`
  excluded) and are always fresh.
- **No free-space field** (decided 2026-07-15; scale reference explains why),
  and no bulk-transfer progress. Do not grow this seam without a demonstrated
  first-workflow need.

## Fingerprint cache (node side)

Hashing is ~30–60 s per GB cold on a Zero 2 W (scale reference), so:

- Extend the `identity.py` stat-signature hash cache with a disk-backed store
  for the assets root, e.g. `~/bopOS/assets/.hashcache.json` — a dot-entry,
  so it is invisible to slot listing, manifest walks, and the host catalog,
  and `_prune` never touches it (prune operates inside a slot). Load at node
  start; write atomically (tmp + rename); garbage-collect entries whose paths
  no longer exist.
- **Seed at fetch completion for free:** the fetcher has just verified every
  file's sha256 (`file_matches` also hashes skipped files) — record
  `(path, stat signature, sha256)` so the post-fetch fingerprint costs a stat
  walk only.
- **Warm in the background at node start**, in a thread throttled/niced so it
  never competes with engine audio. Until a slot is fully covered by valid
  cache entries, report its `fingerprint` as `null`; never block the OSC loop.
- An out-of-band (ssh) edit changes a file's stat signature; the next walk
  re-hashes only that file. `dropassets` may leave stale cache entries for GC.

## Implementation checklist

1. `docs/OSC-CONTRACT.md`: additive §7 bullet parallel to `/os/patches`,
   noted as the 2026-07-15 asset-inventory amendment (v1.6).
2. Node (`python/bopos.py`, `python/identity.py`, `python/fetcher.py` seam):
   the query callback, the persistent cache, fetch-time seeding, startup
   warming.
3. `tools/simfleet.py`: same term, same JSON shape, fingerprints consistent
   with the host catalog for simulated slots; fetch/drop update the simulated
   inventory in the same stitch.
4. Dashboard bridge/state (`dashboard/server.py`): request `/os/assets` on
   device identify, after an asset `/os/fetched` receipt, and after the
   `/os/rev` receipt that follows `dropassets`; while any fingerprint is
   `null`, re-query with capped backoff. Store per-device observed inventory
   with an observed-at marker; distinguish unknown (no reply) from empty.
   Malformed entries: quarantine that entry (mark unknown, log), keep the
   rest of the reply.
5. Non-browser verifier (`verify_*.py`, `~/.venvs/bopos` venv, repo located
   by marker) proving: fresh-start observation with a cold cache (nulls, then
   resolved after warm), post-fetch fingerprint present without a full
   re-hash, out-of-band edit detected via stat signature, drop refresh,
   malformed-entry quarantine, and older-node no-reply handled as unknown.

House rules apply: PD floats are 32-bit (the JSON travels as a string blob,
never through PD), 0-indexing on the wire, no `.pd` edits.
