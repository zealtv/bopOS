# 4-contract-amendment

**Status:** waiting (parent) · after `1`, `2`, `3` are ratified
**Goal:** propose the OSC contract text that falls out of the three rulings.
Bob ratifies; implementing stitches carry it into code.

## Likely in scope

- **§5 definition** — *"device = the computer (one uid, one heartbeat, one
  engine instance)"*.
- **Assignment** — `/all/os/assign …`, `/all/os/to <uid> unassign`, the `-1`
  tombstone.
- **Heartbeat** — `/hb <uid> <id> …` as discovery and ack.
- **§4 Ports** + `docs/PORTS.md` (keep them in sync) — from `2`'s port model.
- **Groups** — if membership moves to the instance.
- **`/pt`** (§4.1) — if element index meaning changes.
- **Engine surface §4.2** — if an instance learns identity/port/channels at
  launch (run context is launch-delivered, never over OSC).

## Fixed constraints

- Pd floats are 32-bit — nothing needing >6 significant figures.
- 0-indexed on the wire and in the model.
- §15 revision-history entry at the then-current version.
- Additive where possible. If it's a hard break, say what breaks. A clean break
  beats a shim (`44/4-cue-retirement` precedent), but manifest/grammar breaks
  reach devices only as fast as patch pushes — as crash-loops (`58`).

## Deliver

Amendment text section by section in `proposal.md`. Mark `.waiting`, surface to
Bob.
