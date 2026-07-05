# dashboard-3-discovery-assign

Phase 3: device discovery and assignment from the dashboard — remove the hand-edited
`bopos.devices` from the critical path.

Checklist:
- [ ] Unassigned pool: new MACs seen on 5550 appear automatically
- [ ] Assign flow: name + ID + drag to position, all from the dashboard
- [ ] Push assignment to the Pi over OSC (needs an `/os/...` set-identity message —
      coordinate with `osc-schema-contract`)
- [ ] `bopos.devices` becomes an export/import format, not the source of truth

This phase is where heartbeat-with-identity (see `osc-schema-contract`) pays off:
IP→MAC correlation hacks go away once `/hb` carries MAC/ID.
