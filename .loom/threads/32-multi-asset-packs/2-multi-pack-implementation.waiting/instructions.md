# 2-multi-pack-implementation

Build the ratified multi-asset-pack design from `1-context-list-design`. Do not
start until that design is ratified; this stitch begins `.waiting`.

## Scope (refine from the ratified design)

- Model multiple packs in `python/bopos.py` (`ASSETS_ROOT` → pack set;
  `installed_assets()` across packs) and `python/runcontext.py`.
- Emit the list of absolute pack paths on the engine context:
  `bash/start-engine.sh` `bopos-context assets …` line and `BOPOS_ASSETS`.
- Land the contract amendment in `docs/OSC-CONTRACT.md`.
- Mirror the new context form in `tools/simfleet.py` (same stitch).
- Surface packs in the Assets workspace as the design dictates.
- If a Bob PD edit is required and not yet done, stay `.waiting` on it.

## Verify

- Browser-free/engine parity check that the engine context receives the pack
  list correctly (simfleet + audition where relevant).
- Ship a guard.
