# Bob's review of the contract amendment — 2026-07-11

Bob reviewed `contract-amendment-draft.md` and approved it **with no spelling
changes** (receiver/address proposals stand as drafted). Ruling: integrate the
thoughts below, then tie this stitch.

## Thoughts from the review, and where each landed

1. **Multi-element dashboard UI direction.** The dashboard currently positions
   devices; to expand to multi-element, let the dashboard define the number of
   elements per device, then render each element as a coloured dot carrying
   the device's number — colour keyed to **element index** fleet-wide (e.g.
   element 1 green on every device, element 2 red, element 3 blue; final
   colours are a UX choice, not fixed here). Fold this in during the
   multi-element implementation.
   → recorded in `seam-3-points-node-side/instructions.md` (which lands the
   true-N element positions) and pointed to from
   `spatial-audio/spatial-1-authoring-ui`.

2. **Dashboard improvements, for later:** (a) set a position by typing a
   number, not only by dragging; (b) a way to define the space with an
   **origin**, so the dashboard layout can be aligned to other plans
   (floor plans, venue drawings).
   → new stitch `dashboard/dashboard-5-position-precision` (loose-end fill,
   deliberately after the current critical path).

3. **Hardware / mute interaction documentation.** How mute interacts with
   different audio boards should be documented — e.g. in the README: how to
   integrate a new piece of hardware or audio interface, what procedure to
   run, and how to fold what was learned back into the repository.
   → new stitch `hw-onboarding-doc` (top-level, agent-workable docs task;
   linked from `audio-input/input-1-hw-recipe` territory — the `set_mute`
   candidate-list note in contract §6 is the seed).

## Applier's editorial delta (flagged, not in the draft)

- §3's parenthetical "(bare `/gain` aliased one transition release)"
  contradicted Edit 8's lockstep ruling; reconciled to "(no bare aliases —
  patches rewrite in lockstep, §13)". Same substance as the ratified Edit 8,
  applied for internal consistency.
- README.md was checked per the checklist: its OSC section (port map, plane
  blurb) does not repeat any amended text — no reconciliation needed.
