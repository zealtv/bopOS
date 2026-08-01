# fp-1-identity-module

Patch content identity, per the ratified fp-0 design (§0 ground truth, §2 —
record in the tied stitch / `.lore/items/2026-07-14-fleet-patch-design-ratified/`).

- Extract the canonical walker + fingerprint from
  `dashboard/server.py:49-98` into `python/identity.py`; the dashboard
  imports it (behaviour identical — existing fingerprints must not change),
  and `bopos.py` uses it to add a `"fingerprint"` key to each `/os/patches`
  listing entry. Keep the stat-signature per-file hash cache.
- Contract amendment: the `/os/patches` fingerprint key, **folded into v1.4
  alongside pe-1's cues amendment** (Bob, Q4 "fold in") — one bump.
  Coordinate with `patch-editor/pe-1-contract-v1.4`: whichever stitch is
  claimed first writes the v1.4 header bump; the other adds its amendment
  text to the same revision.
- Dashboard listing cleaner (`dashboard/osc_bridge.py:426-433`) accepts the
  new key; absent key stays valid (old nodes → identity unknown).
- Mirror in `tools/simfleet.py` and `tools/audition.py` in this same stitch
  (standing rule: new protocol features land in the simulator with the
  feature).
- Verify browser-free: identical fingerprints host vs node walker for the
  same tree; git-managed tree (`.git` ignored) matches its mirrored twin;
  drift (edit one file) changes it; cache correctness after touch/edit.
