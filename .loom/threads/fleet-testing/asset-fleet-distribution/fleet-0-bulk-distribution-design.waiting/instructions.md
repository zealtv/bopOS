# fleet-0-bulk-distribution-design

**Deferred by Bob on 2026-07-15.** Resume when a larger deployment is being
planned or real single-device transfer measurements make fleet coordination
the next operational constraint.

**Start from the revised scale premise**, not the decision record's 10–50 GB
working figure: measured packs are ~1.15 GB and mostly under 5 GB
(`.lore/items/2026-07-15-asset-transfer-scale-reference/` — throughput
assumptions, wall-time table/chart, and the shared-airtime argument that
sequential ≈ concurrent on one access point). Design proportionate to those
numbers and to measurements from the tied single-device workflow (11a/11b).

Write and ratify the bulk-delivery design before implementation. The core,
justified at any scale:

- durable desired slot fingerprints per device (the fleet analogue of the
  11b action, surviving dashboard and node restarts);
- installed-inventory preflight via the 11a seam, plus disk/capability
  preflight if measurements show it matters;
- a bounded, resumable scheduler — a sequential loop over the single-device
  path is the baseline and may simply be enough; one-device-at-a-time
  remains a valid conservative setting;
- honest progress, failure, retry, and offline-device reconciliation;
- engine stop/activate/restart owned safely by the node (builds on
  `fleet-1-node-staged-slot-swap` if tied by then), hot reload only as an
  explicit patch capability.

The rest of the decision record's apparatus is **evidence-gated** — adopt
only when the measured rig demands it, and record the measurement that
justified it: immutable source snapshots, canary + bounded waves per access
point, byte-rate ETA displays, wired origins/caches, USB/SD seeding
orchestration (plain USB/SD seeding for a rare huge load needs no design —
keep the manifest as the verification authority afterwards), packfiles,
chunk storage, rsync/rclone on nodes, peer-to-peer delivery, reliable
multicast.
