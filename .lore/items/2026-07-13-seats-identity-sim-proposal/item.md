# Seats — device identity, binding, and dashboard-managed simulation (dashboard-8 proposal)

Design proposal awaiting Bob's ratification: `installation.json` splits into
**seats** (places in the piece — id, name, element positions, patch, params;
authored before hardware exists, durable) and **devices** (boxes that
heartbeat — uid, hostname, runtime facts only). Binding a device to a seat
fires the existing `/os/assign`; device swap = rebind. One Simulate toggle
spawns the audition rig to inhabit every unoccupied seat with ephemeral
virtual devices (never persisted — the forget-device problem can't recur),
and the listener puck renders only while simulating. One additive wire
change: `hostname` joins `/os/report`. Ends with six open questions (Q1–Q6),
first among them the noun itself.

## Source

Written for `dashboard/dashboard-8-identity-sim-design` in response to Bob's
2026-07-13 composer-experience brain dump. The two survey files are
code-fact inventories (file:line) gathered by subagents the same day.

## Related

- `.lore/items/2026-07-13-composer-experience-brain-dump`
- `.lore/items/2026-07-13-patch-asset-sync-proposal` (sibling proposal, ratified)
- `docs/OSC-CONTRACT.md` §5, §6
- `.loom/tied/preview-3-dashboard-listener-puck`, `.loom/tied/dashboard-3-discovery-assign`

## Tags

- proposal
- decision-record
- device-identity
- simulation
- installation-state
- dashboard
- composer-experience
