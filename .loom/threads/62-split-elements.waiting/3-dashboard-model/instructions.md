# 3-dashboard-model

**Status:** waiting (parent) · design gate · after `1`
**Goal:** device ↔ N Seats in the dashboard: model, Device-tab configuration,
roster, targeting, simfleet.

## Today — one Seat per device, enforced on purpose

- Binding is `seat["bound"] = uid`. Uniqueness enforced by the seed loader,
  `clean_seats`, and `bind` (which **displaces** the other Seat).
- `seat_for_uid` returns the first match; venue rebind keys a dict by uid.
- Device-scoped features assume one Seat: patch pin, Device control panel,
  Assets, audio config, `enabled`.
- simfleet: one id per node.

## Answer

1. **Model** — Seat binds `(uid, slot)`, or device holds a list of bindings?
   Which uniqueness guards change, and what does displacement become?
2. **Configuration** (Bob: *"configured in the device tab"*) — turning split on,
   how many, which Seat each element takes, what happens to the current binding.
   It's destructive, so use the arm → preview → commit → undo pattern from
   `08-control-tab-columns/1-columns-design`.
3. **Roster** — one Devices row, two Seats rows. How each shows the
   relationship, so nobody reboots half a show by accident.
4. **Targeting** — `TargetPicker` and Control's one-card-one-target model should
   need nothing if `1` holds. Verify; record what breaks.
5. **Device vs Seat verbs** — reboot, shutdown, update, pin, audio config,
   `enabled`, identify are device verbs; a Seat card mustn't imply it can reboot
   half a Pi. `08/4/3` already moved device commands to a `Device setup…`
   hand-off — cite it.
6. **simfleet** — what it needs to model a split node for browser journeys.
7. **Io surface** — inherit `59/0a`'s ownership ruling; leave the seam.

## Deliver

`proposal.md` + mockups generated from the running app (`mockup.py` in
`08/1-columns-design` is the precedent). Mark `.waiting`, surface to Bob.
