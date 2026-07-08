# friction-1-starter-kit

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
- [ ] Where does the template live? A separate GitHub repo Bob creates vs a
      `templates/` dir in bopOS cloned out by a script — small DECISION (Bob);
      propose one in the ping, default to in-repo `templates/` if he shrugs.
- [ ] Verify: run the template (minus PD specifics) through the dashboard
      add-patch flow on simfleet; record here.
