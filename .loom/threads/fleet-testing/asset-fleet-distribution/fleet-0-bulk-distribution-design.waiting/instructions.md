# fleet-0-bulk-distribution-design

**Status:** waiting — parked by Bob, 2026-07-15 · design gate
**Resume when:** a larger deployment is being planned, or single-device
transfers show fleet coordination is the next constraint.
**Goal:** a ratified fleet asset-delivery design, sized to measured packs (see
parent), not the old 10–50 GB premise.

## Core (justified at any scale)

- Durable desired slot fingerprints per device, surviving restarts.
- Preflight via the installed-inventory seam (plus disk checks if measurements
  say so).
- Bounded, resumable scheduler — a sequential loop over the single-device path
  may be enough; one-at-a-time stays a valid setting.
- Honest progress, failure, retry, offline reconciliation.
- Node owns engine stop/activate/restart (builds on `fleet-1` if tied); hot
  reload only as an explicit patch capability.

## Only with measured evidence

Immutable snapshots, canary/waves per access point, ETA displays, wired caches,
USB/SD orchestration, packfiles, chunking, rsync/rclone, P2P, multicast. Record
the measurement that justified each one adopted.
