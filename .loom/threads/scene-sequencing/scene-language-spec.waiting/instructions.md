# scene-language-spec

**Status:** waiting — co-design session with Bob. **Do not spec solo.**
**Goal:** a paper spec of the scene scripting language, ratified by Bob, before
any interpreter exists.

Bob's brief: `bob-design-notes-2026-07-08.md` (this folder). Headlines: Ableton
Session-View clip grid (tracks, master scene column, code-box inspector,
one-shot/loop + follow actions), musical + clock time, ergonomic OSC addresses,
high throughput, and node-side spatial primitives (gradients / noise / scatter)
as compact messages.

## Method

1. Study the seeds: `pd/bop/sequences/help.bopseq`, `example.bopseq`, and the bop
   help patches (`param [loop] v1 t1 v2 t2 …`, `- <ms>` waits, `===` sections);
   Bob's intermals notation (https://zeal.co/notebook/intermals/).
2. Write 2–3 real scenes (a Belief-style sweep, a Kite Choir moment, a Plants
   texture) in candidate syntax. Judge the spec by how these read.
3. Cover: loops, one-shots, LFOs, note/random generation, rhythm, trigger / mix /
   crossfade, fleet targeting (all / group / Seat).
4. **Agent-writable** — test literally that an LLM can write a valid scene from
   the doc alone.
5. List what the interpreter needs from the contract — likely events (`/e/*`),
   parameter automation (§3.2), and manifest discovery, most of which now exist.

## Deliver

Spec doc with example scenes + a DECISION list for Bob (core syntax, v1 vs
later). Keep the ratified record in `.lore/`, then tie.
