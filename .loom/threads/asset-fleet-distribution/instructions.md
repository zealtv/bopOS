# asset-fleet-distribution

Deliver safe, observable distribution of asset generations across a fleet.
This is a future goal, deliberately separated from the single-device Assets
workflow so current installations can ship a smaller honest tool first.

The accepted constraints and provisional architecture are retained in
`.lore/items/2026-07-15-asset-management-direction/`. Do not replace the
canonical folder manifest with a mandatory archive or impose media-type
folder semantics.

**Scale premise revised 2026-07-15** (after the decision record was kept):
Bob measured the Belief System pack at 1.15 GB and expects most packs well
under 5 GB — the record's 10–50 GB working premise is superseded for planning
defaults. Numbers in
`.lore/items/2026-07-15-asset-transfer-scale-reference/`: at ~20 Mbps
effective aggregate on shared 2.4 GHz airtime, a measured-scale pack reaches
50 devices inside an evening and 2 GB reaches 20 devices in ~4.4 h. The
likely sufficient design is therefore a **durable desired-slot record plus a
bounded sequential loop over the single-device path**; the heavier machinery
in the decision record (waves, caches, packfiles, P2P, multicast) is
evidence-gated on real-rig measurements, and genuinely huge loads use USB/SD
physical seeding rather than network machinery sized for them.

Children:

- `fleet-0-bulk-distribution-design` — the ratifiable fleet design (waiting;
  deferred by Bob).
- `fleet-1-node-staged-slot-swap` — node-local atomic slot activation
  (waiting; optional hardening, independent of fleet-0 and claimable ahead
  of it).
