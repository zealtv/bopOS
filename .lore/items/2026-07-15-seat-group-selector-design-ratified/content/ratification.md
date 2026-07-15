# Ratification

Bob ratified both the Seat-group selector and nested parameter-address proposals
on 2026-07-15.

For Seat groups this locks:

- lowercase canonical `g<non-negative-id>` selectors;
- multiple groups per Seat and no nested groups in version 1;
- a durable group catalog and Seat membership;
- node-local persisted membership synchronized with the full-state
  `/all/os/groups <uid> ...` envelope and `/os/groups <uid> ...` receipt;
- group scope wherever a numeric Seat selector is legal, retaining explicit
  selectorless, all-only, and UID-only exceptions;
- updates to every member Seat's parameter state, including offline and unbound
  Seats, before emitting one group-targeted OSC datagram;
- selector-only stripping, so `/g1/p/track1/fx/distortion` reaches every engine
  as `/p/track1/fx/distortion`.
