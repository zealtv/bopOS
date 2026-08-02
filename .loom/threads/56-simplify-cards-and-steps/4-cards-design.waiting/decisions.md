# Proposed decisions — awaiting Bob

The following are design output, not ratified implementation authority.

## Settled inputs

- R1: one card targets exactly one of All, one group, or one Seat.
- R2: cards form a grid whose overflow direction is downward.
- R3: order is derived as All, groups, Seats; no drag or stored order.
- R4: Control and Remote use the same card-grid surface.

## Recommended rulings

- D1: render every target as a permanent derived card. No open-card set.
- D2: cards cannot close and there is no `+` action.
- D3: fixed 342px tracks, left aligned, adding tracks as width permits; one
  fluid track only below the single-card breakpoint.
- D4: delete the now-empty Control strip.
- D5: page scroll only. Cards are full height; no per-card scrollport or
  viewport-height clamp.
- D6: the card head is a label and metadata, not a target picker.
- D7: delete Control layout persistence rather than replace it. Venue state is
  the sole source of card membership and order.
- D8: the shipped PresetMenu remains the one provenance treatment. No card
  border, tint, or duplicate header state.
- D9: split the `full` bundle into named host capabilities while sharing one
  CardsGrid. Preserve Remote's dashboard-only declarations, lack of preset
  authoring, and device-command role unless Bob reverses preset Q4 explicitly.
- D10: `feature-backlog/49` inherits touch sizing and Remote page-furniture
  polish, not a divergent card model.

## Questions for Bob

1. Ratify every target always visible (D1/D2), or keep a persisted set of open
   targets with `+` and close?
2. Ratify fixed 342px tracks (D3), or should a partial final track stretch?
3. Does R4 reverse the old “no presets on Remote” ruling? Recommendation: no;
   converge the grid now and leave that explicit capability difference intact.
