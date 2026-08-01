# 1-contract-model-relay

Implement the first ratified seam from
`.loom/tied/param-address-0-design/proposal.md`:

- add the canonical manifest `path + name` qualification helper, validation,
  bounds, and qualified-identity uniqueness while retaining flat compatibility;
- preserve a variable-length `/p/<segment>...` tail through the production and
  audition relays, changing no other OSC plane or strict message shape;
- update simfleet to retain and report distinct qualified parameter identities;
- amend the OSC contract and directly affected reference documentation;
- record any required Pure Data consumer routes in
  `.notes/pd-edits-for-bob.md`; never edit `.pd` files.

Retain a browser-free verifier and exact verification record in this stitch.
Cover valid/invalid manifests, duplicate leaves in distinct paths, duplicate
qualified identities, flat compatibility, production/audition relay parity,
simfleet behavior, preserved argument lists, and the flat/nested x
all/Seat/group selector matrix. The group-selector cases may exercise the
ratified shape ahead of group matching, but this stitch must not implement
Seat-group membership or selector semantics.

Do not implement dashboard persistence/editor behavior or promoted live
controls here. Tie this child only after focused checks and relevant relay
regressions pass; hardware and audible Pd verification remain explicit gates.
