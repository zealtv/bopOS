# zero-2-engine-verdict

**Status:** waiting — co-design with Bob, never solo
**Goal:** a short written verdict on whether bopOS needs a non-Pd engine.

Now part of a larger direction: Bob wants **both Pd and SuperCollider as working
engines** (2026-08-16, `lore:2026-09-25-horizon-architecture-refactor-2026-08-16`). So the
question has shifted from "is SC warranted?" to "what does SC cost and gain on
a Zero?". `sclang` has never launched under the framework.

## Scope (with Bob)

- SC proof-of-concept as a bopOS patch on the Zero.
- CPU comparison vs an equivalent Pd patch (Pd baseline in the parent).
- Why SC: OSC-native, headless, multi-core friendlier, easier for agents to
  write (review §11). RNBO future-only; glance at Faust/Csound.

Agent prep only if Bob asks: research notes on scsynth-on-Zero packaging and a
comparison method. No engine code before the co-design session.
