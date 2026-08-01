# patch-fingerprint-warm

Bob (2026-07-17): the launch-delivered `patch-fingerprint` run-context item
should actually resolve, not read `unknown` forever — and the fix belongs on
the Python side, not PD/SC.

## Design

- `patches/` becomes a persistent hash-cache root exactly like the assets
  root: `bopos.py` loads `patches/.hashcache.json` at startup and warms it
  in a low-priority background thread (mirroring
  `initialise_asset_cache`/`warm_asset_cache`), and re-warms after
  patch-mutating verbs (`addpatch`, `droppatch`, `patch` switch).
- `installed_patches` already hashes every patch synchronously on
  `/os/patches`; persist that work with `identity.save_hash_cache` so a
  listing also warms future launches.
- `python/runcontext.py::resolve_patch_fingerprint` loads the persistent
  cache for the patch's parent directory before consulting
  `identity.cached_directory_info` — still never hashes file contents at
  launch; an unwarmed or stale cache still answers `unknown` honestly.
- `patches/*` is already gitignored, so the cache file adds no repo noise.
- Warming all of `patches/` (not just the active patch) means a patch
  switch launches with a resolvable fingerprint.

Verification: verify script in this stitch directory proving, across real
process boundaries (subprocess running runcontext), that a warmed cache
resolves the fingerprint to the same value as `identity.fingerprint`, that
an unwarmed cache reads `unknown`, and that mutating a file degrades back
to `unknown` until re-warmed.
