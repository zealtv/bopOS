# dist-2 results

The node and simulator now implement OSC contract v1.3 distribution:

- `patch:<name>` fetches converge through a staged, manifest-validated atomic
  replacement under `patches/`; `.git`, traversal, destination symlinks, and
  invalid fetched manifests are refused without mutating the installed patch.
- The exact framework-managed one-release `bop/samplepacks` symlink is safely
  omitted from staging; every other destination symlink is refused. The
  compatibility link therefore cannot copy or prune assets outside the patch.
- Sending the active mirrored patch stops the engine, converges, synchronously
  launches it again, confirms engine liveness, then replies. Stop or restart
  failure produces `err`; active Git patches refuse without disruption.
- Fetches expose additive unicast
  `/os/fetch-progress <slot> <queued|fetching>` states before the unchanged
  terminal `/os/fetched` receipt. Coalesced requesters see the current phase.
- `/os/updatebopos`, `/os/patches`, `/os/droppatch`, and `/os/dropassets` are
  live; `/os/update` and `/os/getsamples` are absent. Reports include hostname
  and contract version 1.3.
- `gdrive:` and `bash/getsamples.sh` are gone; missing/invalid manifests no
  longer fall back to `main.pd`; the launcher exits before starting Jack or an
  engine.
- simfleet mirrors the verbs, listing, progress, Git refusal, active lifecycle,
  coalescing, and per-device serialized fetch queue.
- framework demos are reserved in `.gitignore`; composer patch and asset
  directories are ignored. `clearsamples.sh` now clears canonical
  `assets/samplepacks` directly.

## Compatibility decision

The legacy `patches/<active>/bop/samplepacks` symlink remains for the one-release
window retained by v1.3. Bob's hard-break ruling explicitly retired gdrive,
getsamples, patch-level config, and undeclared launch, but did not retire this
engine-facing path. No `.pd` file was edited.

## Verification

Passed on 2026-07-14:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache PYTHONPATH=python:python/io \
  ~/.venvs/bopos/bin/python \
  .loom/threads/patch-asset-sync/dist-2-node-side.stitching/verify_dist2_node_side.py

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/bopos.py python/fetcher.py python/manifest.py tools/simfleet.py \
  .loom/threads/patch-asset-sync/dist-2-node-side.stitching/verify_dist2_node_side.py

bash -n bash/start-engine.sh bash/clearsamples.sh bash/update.sh
git diff --check
```

The focused verifier reports `all checks passed`. It covers real temporary
file convergence/pruning; staged validation and atomic preservation; arbitrary
and legacy-link symlink cases; `.git` refusal; active stop/restart success and
failure; coalescing; mandatory manifests; listing/drop/update verbs and rev
receipts; hostname; and simulator parity/serialization.

Nearby regression evidence:

- `.loom/tied/fetch-landing/test_fetch_landing.py`: HTTP fresh/no-op/diff,
  prune, Range resume, file sync, validation, invalid slot, and sim checks pass.
  Its old coalescing assertion fails because it stops after the two new progress
  packets instead of waiting for terminal receipts; the focused verifier covers
  the amended sequence and both terminals.
- `.loom/tied/seam-3-points-node-side/verify_points_node_side.py`: helper-level
  point delivery passes 6/6, then the known stale integration setup finds no sim
  device with ID 1 and stops. The master-term harness stops on the same known
  setup issue before its relevant assertions. This is the pre-existing handoff
  gotcha, not a changed-path failure.

Not verified: a real Pi, real engine stop/start and audible continuity, real
LAN/Wi-Fi transfer, or hardware asset consumption. The synchronous launcher
and engine-liveness path is covered with controlled failure injection locally.
