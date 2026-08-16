# 3-dashboard-model

Device ↔ N Seats in the dashboard: the model change, the Device tab split
configuration, targeting, and simfleet parity.

Design gate, downstream of `1-split-identity-model`. Do not implement past it.

## Starting state — the 1:1 invariant is enforced, deliberately

- `seat["bound"] = uid` is the binding (`dashboard/state.py:462-472`), and
  uniqueness is enforced in three places: the `bopos.devices` seed loader
  refuses a uid already bound (`state.py:271`), `clean_seats` drops a
  duplicate on load (`:621-631`), and `bind` **displaces** the other Seat
  rather than erroring (`dashboard/server.py:1126-1139`).
- `seat_for_uid` returns the first match (`state.py:785`) and is used
  throughout; venue rebind builds `{uid: seat_id}` (`server.py:1290`) —
  a dict keyed by uid, so it structurally cannot hold two.
- Device-scoped features assume one Seat behind a device: patch pinning
  (`device_patch_for`, `server.py:1700`), the Device tab's control panel, the
  Assets workspace, audio config, and `enabled`.
- `tools/simfleet.py` models one id per simulated node.

## What must be answered

1. **The model change.** Does a Seat bind `(uid, slot)`, or does a device grow
   a list of Seat bindings? Say which of the three uniqueness guards above
   become `(uid, slot)` guards and which become nothing. The displacement
   behaviour in `bind` is a deliberate UX choice — say what it becomes when a
   uid legitimately holds two Seats.
2. **Where split is configured.** Bob: *"configured in the device tab"*. Say
   what the operator sees and does: turning split on, how many elements, which
   Seat each element takes, and what happens to the existing single binding
   when they do. Splitting is destructive to the current binding, so the
   arm/preview/commit/undo pattern ratified in
   `08-control-tab-columns/1-columns-design` (D-decisions, no dialogs) is the
   house precedent.
3. **What the roster shows.** A split device is one row in Devices and two in
   Seats. Say how the Devices row expresses "this is two Seats", and how a
   Seat row expresses "I share a device" — the operator needs to know before
   they reboot something.
4. **Targeting.** `TargetPicker` (`js/target-picker.js`) and the Control tab's
   one-card-one-target model (`56`, R1) should need **nothing** if the ruling
   in `1` holds — a split element is a Seat and targets like a Seat. Verify
   that rather than assume it, and record anything that does break.
5. **Per-device vs per-seat controls.** Reboot, shutdown, update, patch pin,
   audio config, `enabled` and identify are device verbs; a Seat card on
   Control must not imply it can reboot half a Pi. `08/4/3` already moved
   device commands off the Control column to a `Device setup…` hand-off — that
   ruling helps here and should be cited, not re-litigated.
6. **simfleet parity.** New protocol features land in the simulator in the
   same stitch (house rule). Say what simfleet needs to model a split node so
   the browser journeys can cover it without hardware.
7. **The io surface.** Whatever `0a-io-design-review` rules about peripheral
   ownership arrives here as UI. Do not design it; leave the seam and cite the
   ruling once it exists.

## Deliver

`proposal.md`: the binding model, the Device-tab configuration flow, roster
and targeting answers, the device-vs-seat verb table, and the simfleet note.
Mockups generated from the running app (`mockup.py` in
`08-control-tab-columns/1-columns-design` is the worked precedent), not drawn.

Then mark `.waiting` and surface it.
