# 65-remove-presets

**Goal:** presets are gone from bopOS — code, UI, docs, tests and the contract —
and nothing that remains depends on them.

**Status:** new (2026-10-03). `1` is ready; `2` follows it.

Bob, 2026-10-03: *"I'm going to want to remove presets entirely and clean the
code of the presets."* This is a simplification, not a replacement: don't build
a substitute unless Bob asks for one.

## What presets touch today (rough)

About 950 lines across ~40 files:

- **Host storage and logic:** `dashboard/preset_store.py`,
  `dashboard/preset_application.py`, `presets/` dirs in patch roots
  (`patches/bonks-pd/presets` exists), `HOST_ONLY_DIRS` in `python/identity.py`.
- **Server:** `dashboard/server.py`, `state.py`, `osc_bridge.py`,
  `show_engine.py`, `show_model.py` (preset messages in Show steps, reference
  fingerprints).
- **UI:** Control, Remote (`facilitator.*`), Device panel, Patch editor, Show
  (`PRE` step kind), `preset-menu.css`.
- **Docs:** contract §8.1, `docs/COMPOSING.md`, `docs/GETTING-STARTED.md`,
  `dashboard/README.md`.
- **Tests:** `test_preset_*`, `verify_preset_*`, `verify_show_reference_foundation.py`,
  plus preset assertions inside broader tests.

## Stitches

1. `1-preset-inventory` — find everything, settle the few real questions, write
   the removal plan.
2. `2-remove-presets` — carry it out.

## Constraints

- `.pd` files are Bob's. If a patch uses presets on the Pd side, write the edit
  into `64-pd-edits-owed` instead.
- §8.1 is host-side, not wire, but it's contract text: retiring it is a
  contract amendment with a §15 entry.
- Do this before (or alongside) `66-projects` so the project design doesn't
  have to model presets. Not a hard dependency.
