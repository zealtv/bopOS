# Presets and per-device pins are on their way out

When touching presets, patch pinning, or how installation, venue, show and fleet patch fit together, don't extend them — Bob is removing presets and folding the rest into projects (2026-10-03).

- **Presets go entirely** — code, UI, docs, tests, contract §8.1. No replacement unless Bob asks. Loom `65-remove-presets`.
- **Projects replace the scatter.** A project is a composition with its fleet, its patch (and that patch's iterations), its sites and its show — e.g. Kite Choir: one composition, several iterations, the same fleet, many sites. One patch runs on every device of a fleet; per-device pins and live patch swapping are retired. Loom `66-projects`, a design gate co-designed with Bob — the model isn't ratified yet, so don't implement ahead of it.
- Bob: *"what I'm trying to do is simplify things here so we get a clean surface that's easy to work on and simplify the code base as well."*

## Triggers

- preset
- pin
- pinned
- set_device_patch
- fleet_patch
- venue

## Associations

- [[fix-and-simplify-first]]
- [[decision-gates]]
- [[horizon-refactor]]
