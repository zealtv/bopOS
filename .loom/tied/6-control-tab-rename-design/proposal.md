# Proposal — Dashboard → Control tab rename

Written 2026-07-25 (autopilot). **Awaiting Bob's ratification.**

- **Artifact (mockups):** https://claude.ai/code/artifact/6f9c395e-f7b0-43f3-b132-dbe1ebc2f780#p4
- **Source of record:** `../control-surface-proposals.html` (Proposal 04)

## Recommendation

Rename the live-controls tab to **Control**. Add a **target filter** (All /
Groups / Seat) as a segmented control at the top that scopes the shared surface
(Proposal 03) below it. Keep **cues + master** as a compact strip above the
surface; reserve a **Presets** shelf on the same tab (its contents are 41's
design).

## Open questions Bob must settle
1. Which tab is renamed; does the "Seat" filter reuse the global selected-seat (rec: yes).
2. Cue placement: strip above (shown) vs persistent left rail.
3. Do presets follow the target filter (save "All" vs "Seat 2")? — seam to 41.

**Seam to 41:** the Presets shelf is placement-only; what a preset captures / how
it loads / generator-interpolation are the preset primitive's ratification.
