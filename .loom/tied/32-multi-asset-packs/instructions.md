# 32-multi-asset-packs

**FEATURE.** Support **multiple asset slots** on a node, and deliver them to the
bopOS engine context as a **list of absolute paths of asset folders** — not the
single `assets/` root it gets today.

Bob, 2026-07-23: "I'd like to make sure that we can have multiple asset packs
and, as far as what is being sent to the bopOS context on the device, I'd like
that to be a list of absolute paths of asset folders."

## Where it stands today

The engine gets exactly one assets root. `bash/start-engine.sh` sends
`bopos-context assets $BOPOS_DIR/assets` (and exports `BOPOS_ASSETS` for the SC
engine). `python/bopos.py` has a single `ASSETS_ROOT = .../assets`;
`installed_assets()` lists the immediate children of that one root. The engine
sees one directory and finds slots by convention underneath it.

Bob wants the slots to be first-class and the context to carry the **list of
absolute slot paths** explicitly.

Terminology ruling (Bob, 2026-07-23): each top-level folder remains an
**asset slot**. There is no separate "asset pack" concept; the thread's
directory name is historical.

## Bob gate

This changes the engine-boundary context surface (`docs/OSC-CONTRACT.md` §4.2 /
run context — the `bopos-context assets …` term). That surface is ratified;
amending it is Bob's to sign off. Design first (`1-context-list-design`),
Bob ratifies, then implement (`2-multi-pack-implementation`).

## Constraints / things that will bite

- **PD float precision is irrelevant here (these are strings/paths)**, but the
  PD receiver side (`bopos~.pd` / the `bopos-context` receiver) may need to
  accept a list where it accepts one atom today — that's a **Bob PD edit**
  (house rule: agents never touch `.pd`). Spec it and record it in
  `.notes/pd-edits-for-bob.md`.
- Keep the single-`assets` form working, or migrate deliberately — the
  single-device Assets workflow (tied) and `asset-fleet-distribution` both
  assume one root today. Decide compat vs clean break in the design.
- 0-indexing and absolute-paths-on-the-wire only where the contract already
  is; the slots list is device-local absolute paths (fine — they never go
  through PD as floats).

## Relation to other threads

Adjacent to `asset-fleet-distribution` (bulk rollout) but distinct: this is the
*shape of the slot set and how it reaches the engine*, not fleet distribution.
Note the overlap in the design so we don't duplicate.
