# 56-simplify-cards-and-steps

**Bob's simplification pass, ratified 2026-08-02.** The standing instruction
for this whole thread:

> I want to fix and simplify things before making them more complicated.
> — Bob, 2026-08-02

It came out of a UX review of the shipped Control tab and a three-lens UX
consult. The consult's own recommendations are largely SUPERSEDED by Bob's
answer, which is smaller than any of them: remove a feature, collapse two
surfaces into one, and fix two defects that were hiding underneath.

Read `.loom/legacy-v1/tied/2-multi-target-model/decisions.md` first — it holds
rulings R1–R5 and is the authority for this thread. The three consult documents
sit beside it (`consult-interaction.md`, `consult-workflow.md`,
`consult-systems.md`) and remain useful evidence, but where they differ from
R1–R5, the rulings win. Their Q2 is moot outright.

## The rulings, in brief

* **R1** a column becomes a **card**; a card targets exactly **one** thing
  (all / a group / a seat). Multi-select retires on this surface.
* **R2** cards sit in a grid that overflows **downward**.
* **R3** **no drag-to-reorder** — order is derived: `all`, then groups, then
  seats, the target picker's own ordering.
* **R4** Control and Remote become the **same surface**, intentionally. Remote's
  cards are naturally shorter because `dashboard:` gates Remote only.
* **R5** **`Capture as step` is removed.** Steps are hand-authored.

## Order

Defects first, then the deletion that shrinks the design, then the design.

1. `1-capture-retirement` — R5. Pure deletion, no design gate.
2. `2-step-preset-ordering` — a verified playback defect that breaks
   "a preset with modifications" for hand-authored steps. R5 makes
   hand-authoring the only path, so this stops being cosmetic.
3. `3-preset-dirty-reasons` — a verified provenance defect: three unrelated
   causes render as one `*`. Feeds `53-ui-niggles/3-preset-dropdown-menu`.
4. `4-cards-design` — R1–R4 as a written design. **Bob ratifies.**
5. `5-cards-implementation` — expect to split; it is one stitch today only
   because its shape depends on `4`.

`1`–`3` are independent of each other and of `4`. `4` should not start before
`1` lands, because capture is one of the surfaces the card model would
otherwise have to account for.

## What this thread supersedes

* `55-control-column-targeting` — tied 2026-08-02; this is its successor.
* `1-column-scroll` (tied, commit `a99e982`) fixed the Control column's body
  scroll with `grid-template-rows: auto minmax(0, 1fr)` and `max-height:100%`.
  **R2 retires that mechanism on Control**: a grid overflowing downward scrolls
  the tab, and cards are full height. Expect `5` to remove the clamp and the
  per-card scrollport, and to retire or re-aim
  `tests/verify_control_column_scroll.py`. It is correct for the app as it
  stands and its Remote half may survive; do not treat its removal as a
  regression.
