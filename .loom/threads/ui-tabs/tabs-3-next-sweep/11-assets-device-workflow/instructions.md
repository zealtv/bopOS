# 11-assets-device-workflow

Replace the Assets placeholder with an honest, useful workflow for managing
asset slots on one online assigned physical device at a time. Fleet-wide
desired assets, Sync All, rollout scheduling, and automatic coordinated engine
restarts are explicitly deferred to the separate `asset-fleet-distribution`
thread.

Records:

- Accepted product direction and the deferral boundary:
  `.lore/items/2026-07-15-asset-management-direction/`.
- **Scale premise (revised 2026-07-15):** Bob measured the Belief System pack
  at 1.15 GB and expects most packs well under 5 GB; the 10–50 GB planning
  premise is superseded. Throughput/wall-time/hashing numbers live in
  `.lore/items/2026-07-15-asset-transfer-scale-reference/`. Consequences
  folded here: no free-space field in the inventory seam, fingerprints come
  from a persistent stat-guarded cache, and staged activation is a small
  optional hardening stitch rather than fleet machinery.

Children, in order:

1. `11a-device-asset-inventory` — the additive `/os/assets` observation seam:
   durable, queryable knowledge of the asset slots installed on a device.
2. `11b-single-device-assets-workspace` — the Assets tab workflow: host
   catalog plus explicit send/update/remove for exactly one device.

Related but parked elsewhere: node-local staged slot activation (stage +
atomic swap, removing the live-mutation warning) lives as
`asset-fleet-distribution/fleet-1-node-staged-slot-swap` — it is independent
of fleet design and claimable ahead of fleet-0 whenever Bob pulls it forward,
but it is not required for this thread to tie.

Keep the ratified top-level `assets/<slot>/` deployment boundary. Slot names
and generation suffixes are operator-defined; contents below a slot remain
opaque and engine-neutral. Do not add a media taxonomy or archive transport
here. The parent ties when 11a and 11b are tied.
