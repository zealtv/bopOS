# Implementation decisions

- `ControlColumn` remains the shared renderer while named capabilities declare
  each host: full manifest, preset menu, target picker, exhaustive derivation,
  device commands, and device hand-off. The bundled `full` boolean is deleted.
- Remote's selector list is recomputed from sorted venue groups and Seats on
  every render. It owns no target persistence and emits no picker DOM.
- Derived mode uses `display: contents` only for the component shell and cards
  region, making the individual shipping `.live-card` nodes the grid items.
- Both hosts use page scroll. Remote's footer follows the exhaustive grid
  instead of clamping a nested card body to the viewport.
