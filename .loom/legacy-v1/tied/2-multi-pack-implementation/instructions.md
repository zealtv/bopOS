# 2-multi-slot-implementation

Build the ratified multi-asset-slot design from `1-context-list-design`. Do not
start until that design is ratified; this stitch begins `.waiting`.

## Scope (refine from the ratified design)

- Model multiple slots in `python/bopos.py` (`ASSETS_ROOT` → slot set;
  `installed_assets()` across slots) and `python/runcontext.py`.
- Emit the list of absolute slot paths on the engine context:
  `bash/start-engine.sh` `bopos-context assets …` line and `BOPOS_ASSETS`.
- Land the contract amendment in `docs/OSC-CONTRACT.md`.
- Mirror the new context form in `tools/simfleet.py` (same stitch).
- Surface slots in the Assets workspace as the design dictates.
- If a Bob PD edit is required and not yet done, stay `.waiting` on it.

## Verify

- Browser-free/engine parity check that the engine context receives the slot
  list correctly (simfleet + audition where relevant).
- Ship a living test under `tests/`, organized by the run-context/asset
  surface.
