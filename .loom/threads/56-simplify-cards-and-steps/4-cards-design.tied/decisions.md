# Ratified decisions

Bob ratified the open design questions on 2026-08-02.

## Settled inputs

- R1: one card targets exactly one of All, one group, or one Seat.
- R2: cards form a grid whose overflow direction is downward.
- R3: order is derived as All, groups, Seats; no drag or stored order.
- R4: Control and Remote use the same card-grid surface.

## Review rulings

- R5: Control keeps `+ card`, close, and a single-select target picker on every
  card. It persists the unique set of open targets, never their order.
- R6: Remote shows every target and has no target picker.
- R7: flexible tracks share leftover horizontal space evenly while retaining
  342px as the normal minimum card width.
- R8: Remote shows no presets for now.
- R9: group cards use the current Seats-map slot colour/stroke as their border.
  Unslotted groups use the neutral card border.
- R10: the All card uses a thick white border, backed by the map's dark keyline
  for light-theme contrast. The generated group palette contains no white.

## Consequent design decisions

- D1: Control target membership is versioned persistence. Old ordered column
  records may migrate to their valid unique selectors; ids, order, and picker
  disclosure state do not survive.
- D2: one targetless add draft may exist transiently and is not persisted.
  Already-open targets are disabled in every picker, preventing duplicates.
- D3: the common sort runs after add, retarget, close, migration, and venue
  change. Retarget is atomic and may visibly move the card.
- D4: the add-only Control strip remains. Remote has no strip.
- D5: page scroll only. Cards are full height; no per-card scrollport or
  viewport-height clamp.
- D6: Control heads are picker + metadata + close; Remote heads are label +
  metadata only.
- D7: All/group card borders encode target identity, never dirty/provenance.
  Seat cards retain the neutral face; preset state remains in `PresetMenu`.
- D8: split the host's `full` bundle into named capabilities while sharing one
  `CardsGrid`.
- D9: preserve Remote's dashboard-only declarations, lack of presets, and
  device-command role.
- D10: `feature-backlog/49` inherits touch sizing and Remote page-furniture
  polish, not a divergent card model.
