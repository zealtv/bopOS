# friction-1-starter-kit

**Coordinate first (2026-07-13):** Bob's brain dump
(`.lore/items/2026-07-13-composer-experience-brain-dump`) leans toward
dissolving `templates/` — demo patches live directly in `patches/` (SC demo
akin to the demo PD patch, replacing "default"), and `bopos.config` /
`main.pd`-naming are open questions in `patch-asset-sync/dist-0-proposal`.
That supersedes the RESOLVED note below in spirit; don't scaffold until the
proposal is ratified.

Patch starter-kit / template repo a musician can clone and go.

- [ ] Scaffold the template: repo layout, `bopos.config` example with
      commented explanations, manifest example (params + role + a meter, per
      contract §8), musician-facing README (assume friction-0's docs exist —
      link, don't duplicate).
- [ ] **The `main.pd` skeleton is Bob's** (house rule: agents never write PD).
      Build everything around a placeholder, write a precise spec of what the
      skeleton must do (receive bopos.osc conventions, declare the manifest's
      params), then mark this stitch `.waiting` on Bob's skeleton and ping via
      gremlin.
- [ ] **RESOLVED (Bob, 2026-07-08): the template lives in `templates/` in this
      repo**, copied out by a script or the dashboard.
- [ ] Verify: run the template (minus PD specifics) through the dashboard
      add-patch flow on simfleet; record here.
