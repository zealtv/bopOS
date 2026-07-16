# param-address-1-implementation

Implement the ratified OSC-native nested parameter-address design from
`.loom/tied/param-address-0-design/proposal.md`.

Before coding, split this implementation stitch along the proposal's verified
seams: contract/model/relay and dashboard state/editor. Coordinate the
selector/path cross-product with the separately ratified Seat-group
implementation so variable-length `/p/...` relay lands once. Dashboard
live-control rendering is the downstream consumer owned by
`ui-tabs/.../12-dashboard-live-controls`, not a duplicate implementation here.

Constraints:

- preserve true nested standard OSC through every engine boundary;
- keep existing flat manifests and `/p/gain` behavior compatible;
- never edit `.pd`; retain exact required patch routes in
  `.notes/pd-edits-for-bob.md`;
- follow `docs/VERIFICATION.md`, including the combined
  flat/nested × all/Seat/group matrix.

Bob made this implementation ready on 2026-07-15 and then confirmed that the
unstarted Assets tab carries no sequencing priority. This is now the next
foundation: it precedes Seat-group core, Assets 11a/11b, and Dashboard live
controls.
