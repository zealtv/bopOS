# Proposal — Device-tab "Set patch…" hand-off

Written 2026-07-25 (autopilot). **Awaiting Bob's ratification.**

- **Artifact (mockups):** https://claude.ai/code/artifact/6f9c395e-f7b0-43f3-b132-dbe1ebc2f780#p2
- **Source of record:** `../control-surface-proposals.html` (Proposal 02)

## Recommendation

A **Set patch…** button in the Device-tab patch-diagnostics panel routes to the
Control-tab target picker with the target **pre-selected to this device** (reusing
the bite-2 picker, not a parallel control). For an **unbound** device it first
offers a one-click **"Give this device a seat"** — because pinning needs a seat
(OSC v1.5 targets content by seat), and the operator shouldn't have to learn why.

## Open questions Bob must settle
1. Tab switch (one picker to maintain) vs in-place mini-picker (no context loss).
2. Auto-seat semantics: allocate a hidden/utility seat vs drop into Seats tab to place it.

**Depends on 04** (the picker's home is the renamed Control tab). Grounded in the
bite-2 seatless-control reality — see `../2-device-patch-targeting`'s design note.
