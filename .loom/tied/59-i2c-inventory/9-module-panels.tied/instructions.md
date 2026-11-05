# 9-module-panels

**Status:** after `2`, `3`, `8`
**Goal:** watch a real module's inputs and drive its outputs from the Monitor dock.

Spec: `../0a-io-design-review.tied/proposal.md` (ratified 2026-10-04; Bob's words in `rulings.md`). Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit. Wire changes are ratified as written in proposal §8; write the matching contract text and §15 row as each piece ships.

- A **Modules** tab in the Monitor dock. The only place interactive panels
  live (proposal §4).
- One panel component, drawn from the driver description (`3`):
  - live: inputs in units **and** exactly as the patch receives them
    (numbers plus sparklines); outputs as controls (OLED text, thresholds),
    sent with `io-write`.
  - The header names the source (*Ciro Toast · live*).
- The Device tab's "Show in Monitor" checkbox adds a module's panel and opens
  the device's stream (`8`).
- **Pop-out:** the dock, or one panel, in its own ordinary browser window
  (cross-platform; no Picture-in-Picture).
- Operator writes are refused in Performance. Bob asked for a windowed summary
  (rest, min, max, swing, edges; the retired `4-sensor-test-window`) only if
  live values prove not enough.
