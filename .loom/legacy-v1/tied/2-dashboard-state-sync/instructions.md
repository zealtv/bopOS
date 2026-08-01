# 2-dashboard-state-sync

Implement the dashboard state/synchronization half of the ratified Seat-group
core proposal. Read the parent `shared-seam.md` first; its wire fixtures and
file ownership are the integration contract with the parallel protocol child.

Own only dashboard production files:

- durable validated group catalog and sorted unique group membership on Seats;
- installation and venue save/load behavior (presets remain parameter-only);
- group create/rename/delete and Seat-membership state operations exposed to
  the existing dashboard state API, without building their production UI;
- `/all/os/groups <uid> ...` synchronization for bound physical devices,
  attributable `/os/groups` convergence receipts, bounded retry, reconnect
  replay, `/os/report` reconciliation, and safe bind/unbind/reassignment state;
- group target resolution and durable parameter fan-out helpers needed by the
  downstream live-controls stitch, without adding that control surface or
  sending a second per-Seat OSC fan-out.

Do not touch `python/bopos.py`, `tools/simfleet.py`, `tools/audition.py`, the OSC
contract, dashboard production UI/CSS, promoted live controls, or `.pd`. Test
transport/synchronization against the exact fixtures in `shared-seam.md`; root
will run the combined verifier against the protocol child.

Retain focused state/synchronization verification and a results record in this
child. Cover validation, deterministic IDs, multiple/empty groups, deletion
cleanup, venue round-trip, preset exclusion, offline/unbound membership,
bound-device send, exact/stale receipt handling, retry exhaustion, reconnect
replay, report mismatch repair, bind/unbind/reassignment, and group parameter
fan-out updating all member Seats before one group-addressed send.

Leave the stitch claimed for root review; do not tie or commit.
