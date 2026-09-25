# Sequencer brainstorm session — 2026-07-15

Fable brainstorm on integrating sequencing into bopOS: the Ableton-style clip
launcher idea, the video-texture spatial modulation idea, and how they
synthesise. **Status: brainstorm.** This feeds the Bob-gated `scene-sequencing`
co-design; nothing here is ratified, and all syntax shown anywhere in this
folder is illustrative only.

## Reading order

1. **`01-context-and-constraints.md`** — Belief System lessons, Bob's two
   intuitions, what contract v1.5 already provides, the hard laws. Ends with
   the one-sentence synthesis: *the sequencer is a compiler from behaviours
   into compact terms the fleet already knows how to expand.*
2. **`02-core-proposal-clip-launcher.md`** — the main proposal: grid model
   (track = behaviour + target), **polymorphic clip types** sharing one
   chrome (cue / pattern / ramp / point / field / video / script, all
   round-tripping to text), lookahead scheduling on the shared clock,
   last-writer-wins semantics, shows-as-files, dashboard-tab-with-separable-
   engine placement.
3. **`03-spatial-fields-and-video.md`** — one pipeline (`mask → per-seat
   scalar → param`), three producers: analytic `/field` primitives with
   node-side time evolution (one broadcast per gesture, any fleet size),
   live texture sampling (domesticated, gated), and **video as an authoring
   format baked to ramps** — which keeps Bob's visual workflow while
   dissolving its runtime cost. Plus "the map is the monitor."
4. **`04-language-semantics-sketch.md`** — semantics-only inventory for the
   language co-design (targets, dual time, seeded randomness, scatter and
   spatial spread as primitives), and the observation that `.bopseq`
   (timeline) and intermals (pattern) want to seed *different clip types*.
5. **`05-roadmap-and-first-slices.md`** — the rung ladder. Recommended first
   slice: **Rung 1, cue clips + grid chrome** (Rung 0 cue board on the way).
   Contract-touching rungs flagged (`/field` is the big ask).
6. **`06-wild-ideas.md`** — unfiltered annex (seat personalities, fields
   bound to points, wire-truth visualiser, automation recording, cue echoes,
   everything-is-a-seat).
7. **`90-…` / `91-…`** — independent Codex (GPT-5.5) perspectives
   commissioned during the session: clip-launcher architecture and
   spatial-field/video delivery respectively. `07-codex-synthesis.md`
   extracts what they add or challenge.

## Headline takeaways

- The two intuitions are one system: **video becomes a clip type**, not a
  second sequencer.
- The `/field` term (analytic spatial primitives, node-side evolution,
  `/pt`'s sibling) is the highest-leverage contract idea in the folder.
- Follow actions + cue clips alone recover Belief System's generative
  self-running quality at a fraction of the build — that's the first slice.
- Grid chrome first, language second: Rung 1 needs no syntax decisions and
  produces the working artifact the language co-design should start from.
