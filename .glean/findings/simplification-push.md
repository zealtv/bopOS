# Presets are retired; projects and pin removal are next

When touching patch pinning or how installation, venue, show and fleet patch fit together, don't extend the retired snapshot facility — Bob is folding the remaining model into projects (2026-10-03).

- **Presets are retired** — code, UI, docs, tests and contract §8.1 were removed in Loom `65-remove-presets`. Shared live automation/replay helpers live in `dashboard/live_params.py`. No replacement unless Bob asks.
- **Clean break for old data** — Bob confirmed there are no actual Shows to preserve (2026-10-03). Remove disposable PRE cues and obsolete preset files with the feature; no compatibility loader, migration or replacement store. Preserve unrelated edits and other patch content.
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
