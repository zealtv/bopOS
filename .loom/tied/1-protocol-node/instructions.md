# 1-protocol-node

Implement the protocol/node half of the ratified Seat-group core proposal.
Read the parent `shared-seam.md` first; its wire fixtures and file ownership are
the integration contract with the parallel dashboard child.

Own:

- `docs/OSC-CONTRACT.md` group selector and membership-envelope amendment;
- one canonical selector/membership helper used by real nodes, simfleet, and
  audition rather than three divergent parsers;
- `python/bopos.py` fail-closed membership persistence, selector matching,
  `/all/os/groups` handling, `/os/groups` receipt, `/os/report` fact, and safe
  assignment/unassignment transitions;
- identical matching, envelope, receipt, report, and transition behavior in
  `tools/simfleet.py` and `tools/audition.py`.

Do not touch dashboard production files, group authoring/live controls, or
`.pd`. Preserve the tied variable-length `/p/...` relay exactly: matching a
group strips only the selector and engines never see group identity.

Retain a focused browser-free verifier and results record in this child.
Cover canonical/invalid selectors; numeric/all compatibility; assigned,
unassigned, overlapping, and empty membership; exact full-state replacement;
invalid/duplicate ID rejection; receipt/report attribution; persistence
failure retaining old state with no receipt; restart durability; same-Seat
assignment preservation; direct reassign and unassign clearing; and flat/nested
provided terms through `all`, Seat, and group selectors.

Leave the stitch claimed for root review; do not tie or commit.
