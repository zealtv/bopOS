# d8-3-binding-ux

Authority:
`.loom/tied/dashboard-8-identity-sim-design/` (proposal + ratification).
Needs d8-1; take after d8-2 so occupancy states exist.

The composer-facing seat workflow (proposal §6 walkthrough is the spec):

- [x] **Seat authoring on the map**: click empty space to add a seat (next
      free id, 0-indexed), rename inline, drag to position; element dots
      follow Bob's tied direction (colour = element index, number =
      device/seat id, `seam-3` instructions). Numeric entry/origin stays
      ui-3's job — coordinate, don't duplicate.
- [x] **Bind/unbind flows**: from a seat (pick an unbound device — show
      hostname when reported, uid otherwise; suggested seat name for a
      fresh seat = reported hostname) and from a device row (pick an empty
      seat). Unbind returns the device to the unbound list; seat keeps all
      its data.
- [x] **Sidebar restructure**: Seats (occupancy-badged, ordered by id) /
      unbound Devices (with forget affordance + bulk "forget all offline
      unbound") / Simulate section (d8-2). Heartbeat blips (ui-0) apply to
      whatever rows render — coordinate if ui-0 landed first.
- [x] **Auto-rebind on venue load** surfaced honestly in UI: show which
      seats rebound automatically and which wait unbound.
- [x] verify_*.py Playwright: author-seats-first walkthrough end-to-end on
      simfleet — add seats with no devices, start sim (d8-2), stop, boot
      simfleet devices, bind by hostname suggestion, swap a device between
      seats, forget the rest.
