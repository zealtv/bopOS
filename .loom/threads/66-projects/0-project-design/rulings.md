# Rulings during the design session

Bob's answers while co-designing; `proposal.md` builds on them.

## 2026-10-04 — the model

Framing put to Bob: a project folder replaces `installation.json`,
`installations/` and `shows/`; one project open at a time; the host device
registry (aliases, enabled) stays host-global, outside projects.

1. **Seats per project.** Seats, groups and Seat bindings (which box sits at
   which Seat) belong to the project, like voices in the composition. A site
   holds only the room, listener and Seat positions. One show runs at every
   site unchanged.
2. **Patch iterations are patch folders.** The project lists patch folders
   (e.g. `kite-v1`, `kite-v2`) and marks one live. Patch edit works on a
   folder; pushing it makes it live.
3. **The fleet is the boxes bound to the project's Seats.** No separate
   device list.
4. **One show per project.** Sites change only geometry.
