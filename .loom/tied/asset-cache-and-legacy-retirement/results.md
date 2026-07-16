# Results

The first real `bop000` Assets send exposed two defects and this stitch repairs
both:

- `cached_directory_info()` used `os.walk` traversal order while the canonical
  transfer manifest globally sorts paths. A root `readme.md` plus numbered
  child folders therefore produced `c29d9c…` from inventory for bytes whose
  canonical identity was `c87964…`. The cached path now performs the same final
  path sort.
- engine startup recreated the retired `assets/samplepacks` compatibility
  target and patch-local symlink. Startup now removes only that symlink and an
  empty compatibility target; patch convergence no longer preserves it. The
  obsolete `bash/clearsamples.sh` helper is removed.

Documentation now describes direct run-context asset access. Required future
PD abstraction path edits are recorded in `.notes/pd-edits-for-bob.md`; no
`.pd` file changed.

## Verification

- `verify_asset_cache_repair.py`: **9/9 passed**. Covers canonical nested/root
  ordering, persistence reload, fetch seeding, restart-derived identity,
  retired-symlink rejection, startup cleanup shape, helper removal, and
  contract wording.
- `.loom/tied/11a-device-asset-inventory/verify_device_asset_inventory.py`:
  **27/27 passed**.
- `.loom/tied/11b-single-device-assets-workspace/verify_single_device_assets_workspace.py`:
  **17/17 passed** against a real dashboard and three-device simfleet.
- `bash -n bash/start-engine.sh`, Python compile checks, and `git diff --check`
  passed.
- The older tied `fetch-landing` verifier produced **16 passes and one stale
  assertion**: its coalescing check stops after the two newer `queued` progress
  replies and expects them to be terminal `ok` replies. This predates and is
  unrelated to the repair; the focused fetch-seeding and current 11a/11b
  suites pass.

## Real-device gate

Deployed `python/identity.py`, `python/fetcher.py`, and
`bash/start-engine.sh` to `bop000`; remote hashes matched the local files.
After Bob restarted the node:

- dashboard and node both observed `bop_samplepack` fingerprint
  `c87964c96a705b60316c489b026cd3f555d403cfdc4e511b03a8706fb78f8ceb`;
- inventory reported **39 files / 32,354,451 bytes** and the UI reported
  **current**;
- `assets/samplepacks` was absent and no longer appeared as an extra slot;
- the retired patch-local compatibility path was absent.

The payload was transfer- and identity-verified. Audible sample playback and
the recorded PD abstraction edits were not exercised in this stitch.
