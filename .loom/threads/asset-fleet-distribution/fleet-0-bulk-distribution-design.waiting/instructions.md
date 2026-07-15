# fleet-0-bulk-distribution-design

**Deferred by Bob on 2026-07-15.** Resume when a larger deployment is being
planned or real single-device transfer measurements make fleet coordination the
next operational constraint.

Write and ratify the bulk-delivery design before implementation. Start from
`.lore/items/2026-07-15-asset-management-direction/content/decision.md` and the
single-device workflow's measured behaviour. Cover:

- immutable source snapshots and durable desired slot fingerprints;
- installed inventory plus disk/inode and capability preflight;
- staging, verified whole-slot atomic activation, retained rollback, and
  explicit cleanup;
- persistent resumable transfer journals and activity-based failure detection;
- one canary followed by configurable bounded waves per access point;
- measured byte progress, throughput, ETA, pause/retry/cancel/finalise states,
  and offline-device reconciliation;
- engine stop/activate/restart owned safely by the node, with hot reload only as
  an explicit patch capability;
- wired origins/caches and USB/SD initial seeding;
- evidence gates before adopting packfiles, chunk storage, rsync/rclone on
  nodes, peer-to-peer delivery, or reliable multicast.

Preserve one-device-at-a-time as a valid conservative scheduler setting. Keep
the canonical per-file manifest as end-to-end content identity even when an
optional archive or physical seed transports the initial bytes.
