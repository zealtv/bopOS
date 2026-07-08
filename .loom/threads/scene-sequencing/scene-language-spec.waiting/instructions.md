# scene-language-spec

**Design-only stitch, Bob-gated.** Spec the scene scripting language on paper before
any interpreter exists. Syntax is a creative-instrument decision — Bob ratifies it.

Method:
1. Study the seeds: `pd/bop/sequences/help.bopseq` + `example.bopseq` and the bop help
   patches (`help-bop.sequence.pd` — readable as text; note how bop notates parameters
   and breakpoint automation `param [loop] v1 t1 v2 t2 …`, `- <ms>` waits, `===`
   sections). Then Bob's intermals notation: https://zeal.co/notebook/intermals/
   (semisteps, bitplucking, symbolic ops, `1?004` rhythm durations).
2. Write 2–3 real scenes from past/imagined works (a Belief System-style sweep, a
   Kite Choir moment, a Plants texture) in candidate syntax — the spec is judged by
   how these read, not by grammar elegance.
3. Cover the required features: loops, one-shot lines, LFOs, note/random generation,
   rhythm notation, scene trigger/mix/crossfade semantics, and fleet targeting
   (per-device / group / all — how a line addresses devices).
4. **Agent-writability is a design goal**: plain text, forgiving grammar, documented
   by example, diff-friendly (scenes are files in git). An LLM should be able to write
   a valid scene from the doc alone — test this literally.
5. State what the interpreter will need from the contract (`/cue`, patch parameter
   discovery) so `osc-schema-contract` can reserve it.

Deliverable: a spec doc with the example scenes + a **DECISION** list for Bob (core
syntax, what's v1 vs later). Mark `.waiting`, get Bob's ruling, keep the ratified
record in `.lore/`, then tie. Interpreter/UI work stays in the parent thread.

---
**2026-07-08: Bob's design brief captured** — see
`bob-design-notes-2026-07-08.md` in this stitch. Headline: deferred until after
the dashboard, then a dedicated co-design session with Bob (do NOT spec solo).
Key inputs: Ableton session-view clip grid (tracks, master scene column,
codebox inspector, oneshot/loop + follow actions), musical + clock time, OSC
address ergonomics, high throughput, node-side spatial primitives (gradients /
noise / scatter) sent as compact messages — which, if they land, mostly
dissolve `video-mask`.
