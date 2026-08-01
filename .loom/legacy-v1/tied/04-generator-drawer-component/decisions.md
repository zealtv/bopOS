# Decisions

## Value and stop in the Show inspector

`value` is not a generator kind, so it remains the ordinary typed value field
above the drawer. `stop` is a momentary action, so it sits beside `Value` in
the drawer's action column. Neither appears as a fourth or fifth latching tab;
the shared tab set is exactly `LFO | loop | fade`.

When a value or stopped message opens the drawer, it receives a usable LFO
draft with no generator tab falsely shown as active. Choosing a generator tab
persists that kind's canonical default arguments onto the focused message.
The existing Show message model remains the draft store, while
`generatorDrawerState` keeps disclosure state outside heartbeat-rebuilt DOM.

## Fixed dimensions

The component is exactly 320px wide. The old `min(320px, 100%)` width and
small-screen field reflow were removed: the drawer is an instrument face and
does not change internal geometry. The Show inspector grows from 300px to
376px so its padding and the drawer both fit; later app-level reflow remains
owned by stitch `06-control-panel-reflow-and-editor`.
