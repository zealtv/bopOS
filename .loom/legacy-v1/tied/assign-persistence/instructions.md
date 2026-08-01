# assign-persistence

**Do first (with `hb-identity`) — Crux 1's other half, amended by Bob's ratification:
node-side persistence is required; standalone operation is first-class.**
Contract: `docs/OSC-CONTRACT.md` §5, §10. Reasoning: `schema-design-draft` (tied) —
`ratification.md` Crux 1.

- `/all/os/assign <uid> <id> <name> [posx posy pos2x pos2y]` — idempotent
  **full-state** (positions ride in it; no separate pos verb). Matching node applies
  id/name/positions, sets hostname (today's `/config` behaviour), tells the engine its
  id, acks by heartbeating the new id.
- **Persist the assignment node-side** on persistent hosts — build the framework
  persistence store (`/os/store` / `/os/load`, contract §10) or at minimum its file
  layer, and store the assignment in it. A fleet configured from the dashboard must
  run standalone after the network is removed (active installs work this way today).
- **Boot resolution order:** local persisted assignment → `bopos.devices` seed →
  unassigned (id −1, fast heartbeat, announcing). `bopos.devices` becomes an optional
  seed, never a gate — the unknown-MAC silent failure in `helper.py:47-48` dies here.
- Ephemeral (`update_model: ephemeral`) hosts skip persistence and re-hello each boot.

Verify in simfleet: assign a fake node → kill the "network" (stop the dashboard side)
→ restart the node → it comes back with its persisted id, no dashboard present. Then:
reboot an ephemeral node → it re-hellos and is re-assigned.
