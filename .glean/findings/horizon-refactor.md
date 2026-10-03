# One device, one engine, probably Pd — the assumption on its way out

When a design touches engines, launch, ports or per-device identity, phrase it so it survives several engine instances per device and a non-Pd engine.

Bob (2026-08-16) set a marker, not a plan: split elements (one engine instance per element, each its own Seat — loom `62-split-elements`) and engine agnosticism (*"we are going to want both pd and super collider as working engines"*) are one refactor. Say "engine instance", not "the Pd". `sclang` has never launched under the framework. Read `lore:2026-09-25-horizon-architecture-refactor-2026-08-16`; the why is `lore:2026-09-25-architecture-review-2026-07-05` §11.

Order is Bob's to set. The queue was cleared on 2026-10-03 for a reassessment; earlier he'd put i2c (`59`) before `62`. Projects (`66`) assume one patch per fleet, which fits `62`'s "same patch in every instance".

## Triggers

- split elements
- SuperCollider
- engine agnostic
- start-engine.sh

## Associations

- [[decision-gates]]
- [[simplification-push]]
