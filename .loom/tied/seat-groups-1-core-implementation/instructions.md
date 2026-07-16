# seat-groups-1-core-implementation

Implement and verify the non-visual foundation of the ratified Seat-group
proposal:

- amend the OSC contract for lowercase canonical `g<id>` selectors and the
  full-state membership envelope/receipt;
- add fail-closed node-local persistence and selector matching;
- land identical behavior in simfleet and audition nodes;
- add durable dashboard group catalog and Seat membership to installation and
  venue state;
- add acknowledged membership synchronization, reconnect replay, report
  reconciliation, and safe assignment/unassignment transitions.

Before coding, split this stitch into focused protocol/node and dashboard-state
children if it cannot be completed and verified as one bounded change. Reuse
the ratified nested-parameter variable-length relay foundation; do not add a
second engine-address path. Follow `docs/VERIFICATION.md` and do not edit `.pd`.

Bob made this implementation ready on 2026-07-15. It follows the nested
parameter contract/model/relay foundation. The sibling spatial UX design should
be sent to its review gate early; core work may proceed while that review waits.
