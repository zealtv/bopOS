# 2-seat-device-names

Bob, 2026-10-27: "on the seats tab it would also be good to have an option to
show the device names assigned to a seat."

## What exists (read 2026-10-27)

- `spatial.js` draws each Seat as a dot with only `seat.id` inside it
  (`.element-number`, ~146). The bound device appears only in the `<title>`
  tooltip, and even there only as the Seat and its groups, not the device.
- The node's device comes from `devices[seat.bound]`, or from a virtual
  device whose `seat_id` matches in Simulation. Names come from
  `Identity.primary(device, installation)` (`device-identity.js`): the
  custom alias, e.g. "Bria Fox", or the generated name.
- `#assigned` in the sidebar lists Seats; check whether its rows already
  name the device before adding anything there.

## Do

- Add a "Device names" toggle to the map. A check in the Seats section head
  or `#point-toolbar` seems the natural place. Match the design-language doc
  that glean `dashboard-vocabulary` cites. When it's on, draw the bound
  device's name as a label beside each Seat's dot (both elements of a paired
  Seat get the label only once, on the first). Unbound Seats show nothing,
  or a dim "unbound"; choose and record which.
- Remember the toggle per viewer in localStorage with try/catch, the same
  way `bopos.device-sort` works in `dashboard.js`. It defaults to off, so
  the map looks the same as today.
- Labels must stay readable in both themes. They must not catch pointer
  events, so dragging and double-click pairing keep working. They also need
  to hold up when Seats sit close together; long names can be truncated with
  the full name kept in the `<title>`.
- Labels must not flicker on heartbeat re-renders (the map redraws on every
  heartbeat; see the 0b416d8 heartbeat-blip fix for the trap).
- Consider also adding the device name to the Seat's `<title>` and
  aria-label whether or not the toggle is on. It costs almost nothing.

## Verify

A Playwright journey on private ports with two bound Seats (custom aliases),
one unbound Seat and one paired Seat. Check:

- the toggle defaults to off, with no labels;
- when on, the labels show the aliases, appear once per Seat, and still show
  after a reload;
- a drag still moves a labelled Seat;
- 390 px width works.

Include screenshots for Bob in both themes.
