# Handoff — 2026-07-12 (boundary 4 tied)

## Loom

- `boundary-4-pd-edit-wave` is tied as `.loom/tied/boundary-4-pd-edit-wave`.
- The next loose end on the engine-boundary chain is:

  `engine-boundary-design/boundary-6-contract-v12-and-renames/boundary-5-launch-context-and-topology`

- Resume with:

  ```sh
  ./.loom/loom claim boundary-5-launch-context-and-topology
  ```

## What landed in boundary 4

- Bob completed the Pure Data rewrite wave:
  - `pd/bopos.pd` replaced `pd/bopos.osc.pd`
  - the common engine ingress is the selector-stripped localhost 6661 surface
  - active patch code was rewritten to the ratified `bopos-*` buses
- Agent-side support updated `python/helper.py` so helper-driven
  lifecycle/provision notifications now emit only `/notify <event>`.
- A stitch-local static verifier was added:

  `.loom/tied/boundary-4-pd-edit-wave/verify_boundary4_pd_wave.py`

## Verification completed

- Static verifier:

  ```sh
  ~/.venvs/bopos/bin/python .loom/tied/boundary-4-pd-edit-wave/verify_boundary4_pd_wave.py
  ```

  PASS — common-surface buses present, legacy PD transport/report symbols absent,
  no shipped/reference PD patch retains `6660` or `5550`, and helper no longer
  emits legacy top-level lifecycle/provision engine notifications.

- Python compilation:

  ```sh
  PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
    python/helper.py .loom/tied/boundary-4-pd-edit-wave/verify_boundary4_pd_wave.py
  ```

  PASS.

- Production-style macOS N=1 gate:
  - Pd 0.55.2 owned UDP `6661` and `6662`
  - Pd did not own `6660` or `5550`
  - injected to `127.0.0.1:6661`:
    - `/id 7`
    - `/os/master 1`
    - `/p/gain 0.75`
    - `/pt 0 0 0.5`
    - `/cue snap`
    - `/notify identify`
  - Bob confirmed audible success: “got sound”

Full notes are in `.loom/tied/boundary-4-pd-edit-wave/results.md`.

## Honest gaps carried forward

- We did not retain a dynamic artifact for `to-bopos-io` observed on `8880`.
- We intentionally did not exercise `to-bopos-report` because the active patch
  did not expose a live report sender path and the session constraint was to
  avoid modifying `.pd` for the test.
- We did not re-check clean post-stop release of `6661` and `6662` after the
  audible gate.

These were recorded in the stitch results rather than treated as passed.

## Repo state note

- The worktree is still dirty outside boundary 4. That is expected here; do not
  assume the repo is commit-clean.
- The next session should preserve unrelated edits and work only the next loom
  stitch unless Bob directs otherwise.
