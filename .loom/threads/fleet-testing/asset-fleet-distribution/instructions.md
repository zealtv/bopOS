# asset-fleet-distribution

**Status:** parked by Bob, 2026-07-15
**Goal:** safe, observable rollout of asset packs across a whole fleet. The
single-device Assets workflow already ships; this is the fleet layer on top.

## Scale premise (revised 2026-07-15)

Packs are ~1.15 GB measured, mostly < 5 GB — not the 10–50 GB the original
decision record assumed. At ~20 Mbps shared airtime, a measured-size pack
reaches 50 devices in an evening. So the likely design is **a durable
desired-slot record per device + a bounded sequential loop over the
single-device path**. Heavier machinery (waves, caches, P2P, multicast) only if
real measurements demand it; huge loads go by USB/SD.

References: `.lore/items/2026-07-15-asset-management-direction/`,
`.lore/items/2026-07-15-asset-transfer-scale-reference/`. Don't replace the
folder manifest with a mandatory archive or impose folder semantics by media
type.

## Stitches

- `fleet-0-bulk-distribution-design` — the fleet design, for Bob.
- `fleet-1-node-staged-slot-swap` — atomic slot updates on the node. Optional
  hardening; independent and claimable first.
