# Decisions — 41-preset-primitive/1

**The proposal is RATIFIED in full (Bob, 2026-07-28, live session).** All four
forks are ruled below; implementation proceeds on it, after the review stitch.

## 2026-07-28, Bob, live session — the four forks

- **F1 — `presets/` is excluded from the distribution fingerprint.** Bob:
  "excluding presets/ is fine." `presets/` becomes a named host-only patch
  subdirectory: authored content that travels with the patch in git, invisible
  to `identity._walk_files`, the distribution manifest, the fingerprint, and
  prune-to-manifest convergence. Saving a preset therefore never restages the
  fleet patch.
- **F2 — `morph` (generator-argument interpolation) is the interpolation
  mechanism.** Bob: "morph is great." The output-crossfade mix function is
  **not** adopted; §3.3's one-slot / last-writer-wins model stands, and a
  literal shape crossfade stays authorable as two steps if it is ever missed.
- **F3 — capture-as-step captures only targets that have a preset applied.**
  Bob: "capture-as-step doesn't include non-targets." Un-preset targets are
  omitted and the button states the count before committing. No anonymous
  value-snapshot messages are minted implicitly.

- **F4 — the applied-preset marker is stored provenance with derived
  dirtiness.** Bob asked for the reasoning before ruling, then took position 3
  of the revised §10 F4 ("that sounds good"). `applied_preset` stores
  `{patch, name}` only and is cleared solely by recalling another preset or
  choosing none; whether the target still equals the preset is **computed at
  render** from durable values and automation entries, never stored as a flag.
  This follows the entity review's ratified R5 (verdicts derived, never
  stored) rather than the hardware-synth sticky dirty bit, which lies once a
  value is returned to its preset position. Comparison happens at the
  precision the UI sends; generator entries compare by argument list; a morph
  in flight reads dirty until it settles. Provenance is runtime state,
  forgotten on dashboard restart like automation state.

## Also ruled

- **A review stitch precedes implementation** (Bob, same session): another
  agent reviews this proposal in detail before any of it is built. The
  implementation stitches are therefore *not* created here — the review may
  reshape them. See `41-preset-primitive/2-proposal-review`.
