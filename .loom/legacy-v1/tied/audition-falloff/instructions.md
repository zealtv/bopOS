# audition-falloff

**Goal (Bob, 2026-07-17):** in the Seats tab, the listener-direction widget
becomes draggable in and out to control the audition mix falloff — pulled
close to the listener means a short radius/fast falloff, extended further
means a longer falloff and a larger audible radius. The audition mix also
becomes forward-biased: you can't hear behind you as well as in front.

Bob specified this UX himself, so the facilitator-view decision gate is
satisfied; no proposal round needed.

Children in order: 1-forward-bias (pure geometry, ships alone) →
2-range-widget (dashboard UI + wiring + Playwright verify).

This is all on the private dashboard↔audition plane (`/audition/listener`
`x y heading-deg range-m`) — no OSC-contract change is needed; the frame
shape already carries `range_m`, only who chooses its value changes.
