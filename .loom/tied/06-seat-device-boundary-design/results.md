# Seat / Device boundary design status

## Outcome

The short ratification proposal is complete and ratified by Bob. It covers the
canonical Seat/Device records, map-first and device-first binding over one edge,
atomic Seat ID/preset reindex, one physical roster, and the smallest allowlisted
UID-targeted administration envelope.

Review exposed one necessary addition: removing or replacing a binding must
also clear the physical node's persisted assignment. The proposal therefore
adds an idempotent `unassign` handshake and records that the admin seam must land
before Seats exposes those mutations.

## Verification

Documentation/contract design review only:

- checked current state persistence, venue loading, preset shape and binding
  handlers;
- checked current node OSC dispatch, admin verb allowlists, heartbeat and reply
  attribution;
- checked terminology against OSC contract v1.4 and the ratified seats-first
  design;
- independent read-only review completed and incorporated;
- `git diff --check` passed.

No implementation, OSC contract edit, node behavior, browser behavior,
hardware, audio, or `.pd` patch was changed or tested. The implementation
dependency is now 08 before completion of 07, followed by 09.

