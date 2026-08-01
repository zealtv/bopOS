# Ratified listener-range design

Bob ratified 2026-07-21, in session. The design is `proposal.md` in this stitch
(kept as lore `2026-07-21-listener-range-ux-proposal`): **alternative A + D** —
a fixed radial scrub collar on the listener dot for range magnitude, a shortened
fixed-length heading handle that no longer writes range, and a typed numeric
field for the keyboard/precision path. Range renders as a room-clipped radial
gradient with a thin outline (dashed where it leaves the room, solid at the
ceiling), drawn from `--sim` and `--accent-cyan` only.

Bob's rulings on the five open questions:

1. **Scrub gain: 2.5×** (relative pointer-distance delta), not pointer-absolute.
2. **Ceiling: keep the room diagonal**, for now. No server change —
   `dashboard/state.py:733` clamps too, and a two-plane change is not wanted here.
3. **Heading handle: 0.9 m**, i.e. expressed in metres, not screen pixels.
4. **Listener bar: in the map toolbar**, not the Seat sidebar.
5. **The knobbly line leaves a residual tick** — it does not vanish entirely.

Everything else in `proposal.md` stands as written. Implementation is
`02-listener-range-implementation`, which this ratification unblocks.
