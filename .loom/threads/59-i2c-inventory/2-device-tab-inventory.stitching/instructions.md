# 2-device-tab-inventory

**Status:** after `1`
**Goal:** the Device tab is the IO inventory: bus, declared modules, status, errors.

Spec: `../0a-io-design-review.tied/proposal.md` (ratified 2026-10-04; Bob's words in `rulings.md`). Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit. Wire changes are ratified as written in proposal §8; write the matching contract text and §15 row as each piece ships.

- Scan: addresses hex and sorted, hints never claims (`0x48 · ADS1x15?`); three
  states (no bus / bus but empty / not scanned); kernel-claimed (`UU`, e.g.
  the DAC) marked. A Scan trigger plus "last scanned".
- Declared modules for this device (from `3`): running / missing (optional OK,
  required flagged) / errored with the bridge's reason; **Re-init** per row; a
  snapshot of current values.
- **"Show in Monitor"** checkbox per module (proposal §4). It does nothing
  until `9` adds the panels; hide it until then if that's cleaner.
- Use the shipped components (§12). Browser journey covering all three
  scan states and module states via simfleet.

## Remaining: Re-init (ratified 2026-10-04, proposal §8d)

Build `io-reinit` per §8d and a **Re-init** button per module row (enabled in Performance; disabled offline or while pending). Optional/required missing display is already done (a569058).
