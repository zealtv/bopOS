# Verification (2026-10-27, main at 28447de + this change)

`tests/verify_seat_device_names.py`: a real dashboard on private ports, four
physical-protocol peers (from `verify_device_roster_sort`), a paired Seat 0
(Dora Vale), Seat 1 (Abel Fern) and an unbound Seat 2. It checked:

- the toggle is off by default, with no labels and no names in the list;
- the tooltip names the device with labels off;
- when on: one label per bound Seat (Dora once despite two elements), none
  on the unbound Seat, and the list rows show both names;
- labels are still there after 2.5 s of heartbeat re-renders, and they never
  take the pointer;
- a labelled Seat still drags;
- the setting survives a reload;
- there's no horizontal scroll at 390 px;
- turning it off clears the labels, and there are no page errors.

Neighbouring journeys still pass: `verify_control_tab`,
`verify_device_roster_sort`, `verify_spatial_cancel`, `verify_ground_and_card`.

Screenshots: `names-dark.png`, `names-light.png`, `names-390.png`.
