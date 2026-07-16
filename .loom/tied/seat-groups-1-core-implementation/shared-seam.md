# Seat-group core shared seam

This is the integration contract for the parallel core children. The ratified
proposal remains authoritative; these fixtures make its implementation choices
deterministic without changing product scope.

## Canonical identities

- Wire selector: `g<id>` where ID is a non-negative signed-int32 value.
- Valid examples: `g0`, `g1`, `g27`, `g2147483647`.
- Invalid examples: `g`, `G1`, `g01`, `g-1`, `g+1`, `g2147483648`.
- Stored group IDs are integers, unique and sorted ascending. Display-name
  changes never alter the ID.
- A Seat's membership is a complete sorted unique list. Groups contain Seats;
  an unbound Seat retains membership, while a node assigned ID `-1` never
  matches any group.

## Wire fixtures

```text
/all/os/groups <uid:string> <group-id:int32>...
/os/groups     <uid:string> <group-id:int32>...
```

The command tail replaces the complete set; an empty tail clears it. Real,
simulated, and audition nodes validate the whole message before changing
memory or disk. Invalid or duplicate IDs, a UID mismatch, or persistence
failure changes nothing and emits no success receipt. Success persists first,
then installs the complete set, then returns an attributable receipt in sorted
order. `/os/report` exposes the same sorted `groups` array.

`g<id>` is legal wherever a numeric Seat selector is legal, subject to the
existing selectorless, literal-`all`, and UID-envelope exceptions. Matching a
provided term removes exactly one selector:

```text
/g1/p/gain 0.5                    -> /p/gain 0.5
/g1/p/track1/fx/distortion 0.5    -> /p/track1/fx/distortion 0.5
```

## Transition fixtures

- Repeating assignment to the same Seat preserves node membership.
- Direct assignment to a different Seat persists an empty group set before the
  new ID becomes routable; dashboard replay supplies the new Seat's set.
- Unassignment atomically persists empty groups and ID `-1` before success.
- Dashboard membership belongs to Seats and survives bind/unbind/replacement.

## Dashboard convergence fixtures

- Dashboard sends one literal `/all/os/groups <uid> ...` full-state envelope
  for a bound physical device; it never expands groups into numeric sends.
- An exact attributable receipt converges the pending write. A stale or
  mismatched receipt/report schedules the latest full state again.
- Reconnect and new binding replay the bound Seat's full membership; unbound
  and offline Seats retain authored membership without pretending convergence.
- Group parameter fan-out updates every member Seat, including offline and
  unbound Seats, before emitting one `/g<id>/p/<qualified...>` datagram.

## Parallel ownership

- Protocol child owns contract, shared protocol helpers, node, simfleet, and
  audition production files.
- Dashboard child owns dashboard backend/state production files and uses a fake
  transport in focused tests.
- Neither child owns production UI, CSS, live controls, or Pure Data.
- Root owns combined verification, conflict resolution, and Loom transitions.
