# 4-cards-design

**Design gate — Bob ratifies.** Turn R1–R4 into a written design, then stop.
Do not implement past it.

Bob's own statement of the model, 2026-08-02:

> Rather than thinking about these as columns, let's call them cards. A card has
> a target picker and a card can target exactly one target, be it all, group or
> a seat. […] they are essentially in a grid that overflows down not
> horizontally […] In this way both remote and control tabs can be the same and
> remote will naturally present shorter cards because it's a subset of the
> parameters of the patch.

and, amending his own first sketch:

> dragging to reordering isn't actually required. We can order by all, then
> groups, then seats, just the same way that the target picker does.

## The ruled decisions — settled input, not open questions

* **R1** one card, one target (`all` / a group / a seat). Multi-select retires
  here. `TargetPicker` keeps multi-select for its other consumers — check them.
* **R2** cards in a grid that overflows **downward**.
* **R3** order is **derived** — `all`, then groups, then seats. No drag, no
  stored order, no reorder affordance.
* **R4** Control and Remote are the **same surface**.

## What the design must actually decide

1. **What replaces `bopos.control.columns`.** R3 kills stored order, and R1
   kills the per-host multi-selection. What persists — the SET of open cards?
   Nothing at all (every target always has a card)? "Every target always has a
   card" is the simplest thing that could work and deserves to be considered
   seriously before a persistence model is kept out of habit. Note the D5
   prune, the `venueKnown` gate (`08/4/3`) and gotcha 20 all exist to serve
   restored per-column state; several may become deletions.
2. **Whether a card can be closed at all**, and what a `+` means when order is
   derived and every target is already representable.
3. **Card width and the grid.** The 342px track and the dropped 1400px cap were
   `1-columns-design` D2/D3 for a horizontal strip. A downward grid is a
   different problem; restate rather than inherit.
4. **What happens to the strip.** After `1-capture-retirement` its right-hand
   slot is empty and `+` may be gone too.
5. **Remote's convergence.** Remote today is one column with a picker, on a
   tablet-first document. Name exactly what changes there and what
   `feature-backlog/49-remote-ipad-restyle` inherits. **R4 supersedes** Bob's
   earlier "don't change Remote while we work on Control" — he confirmed the
   convergence is intended — but 49 still owns the touch pass.
6. **Per-card scroll versus page scroll**, and therefore the fate of
   `1-column-scroll`'s `minmax(0, 1fr)` clamp and
   `tests/verify_control_column_scroll.py`. R2 implies the page scrolls and
   cards are full height.
7. **The card head.** It is the closed target picker (D4). With one target and
   derived order, does it still need to be a picker at all, or is it a label?
8. **Where provenance state shows**, coordinating with `3-preset-dirty-reasons`
   and `53-ui-niggles/3-preset-dropdown-menu`. Do not design a second treatment.

## Evidence

The three consults are at `.loom/legacy-v1/tied/2-multi-target-model/`
(`consult-interaction.md`, `consult-workflow.md`, `consult-systems.md`). Their
Q1 material is directly relevant and two of three independently reached R1 —
including the traffic argument worth carrying into the design: `apply_preset`
coalesces to one datagram per param only for a single `all`/`gN` selector
(`server.py:2126-2137`). Their Q2 is moot under R5.

Read before proposing: `1-columns-design/decisions.md` (all nine, D1–D8), the
`07-target-selector-component` record, and design-language §12 (ground and card)
and §18.

Generate mockups from the **real running app** the way `1-columns-design` did
with its `mockup.py` — not drawn, and not described in prose alone. Bob reviews
pictures.

## Deliverable

`proposal.md` + `decisions.md` in this stitch, then `.waiting` on Bob. Where the
design forces a choice Bob has not made, put it to him as a numbered question
with a recommendation rather than picking silently.
