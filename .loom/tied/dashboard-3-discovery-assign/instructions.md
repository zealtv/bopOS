# dashboard-3-discovery-assign

Phase 3: device discovery and assignment from the dashboard — remove the hand-edited
`bopos.devices` from the critical path.

**The protocol side is now specified — `docs/OSC-CONTRACT.md` §5–§6** (ratified
2026-07-07; implemented by `osc-schema-contract/hb-identity` + `assign-persistence`).

Checklist:
- [ ] Unassigned pool: nodes heartbeating `id = -1` (fast, ~2 s) appear automatically,
      keyed by `uid` — never by source IP
- [ ] Assign flow: name + ID + drag to position, all from the dashboard, one tap on
      `/os/identify` to chirp/flash the physical box
- [ ] Push `/all/os/assign <uid> <id> <name> [pos…]` — idempotent full-state; the node
      persists it (standalone operation after network teardown is first-class)
- [ ] Dashboard keeps a persistent `uid → assignment` table; `bopos.devices` becomes
      a seed/export format, not the source of truth
