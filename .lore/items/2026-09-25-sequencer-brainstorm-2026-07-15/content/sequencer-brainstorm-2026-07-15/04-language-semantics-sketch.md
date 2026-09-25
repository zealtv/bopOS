# Scene language — semantics sketch (NOT a syntax proposal)

*Fable brainstorm, 2026-07-15. Bob's standing ruling: the language is a
co-design, never solo. This note deliberately stops at semantics — what the
language must be able to *mean* — plus observations about the seeds. Any code
blocks are illustrative pseudo-notation to make semantics concrete, not
candidate syntax.*

## The semantic inventory (what a clip script must express)

1. **Time**: waits and positions in *both* clock time (ms/s) and musical time
   (bars.beats, subdivisions), mixable per clip; loop length; swing later.
2. **Events**: fire a cue; set a param; both with a **target** (inherit from
   track, or override per line with selector `all | gN | id`).
3. **Trajectories**: ramp a param through breakpoints (`.bopseq` pairs are the
   proven seed: `param v1 t1 v2 t2 …`); LFO as a first-class generator
   (shape, rate, depth, offset) that *compiles to node-side evolution*, never
   dashboard streaming.
4. **Randomness, seeded**: choose from sets (samples, cues, values in a
   range, seats in a group), weightings, densities — everything derives from
   the run seed so a show replays.
5. **Scatter as a primitive**, because it was a whole M4L device last time
   and it should be one word now. Semantics: over some window, fire an event
   on each seat with probability p (or exactly-k seats). Wire trick worth
   ratifying: broadcast the event with `(seed, p, window)` and let each node
   coin-flip `hash(uid, seed) < p` and pick its own offset inside the window
   — one broadcast produces a fleet-wide deterministic scatter, replayable,
   zero per-seat messages. (A dashboard-side fallback that unicasts the
   choices is semantically identical for small fleets.)
6. **Paths/sequences through space**: "this event walks seat to seat along an
   ordering" — orderings come from the seat map (by position along an axis,
   around the hull, by group, by explicit list). Belief System did this by
   hand-sequencing MIDI notes; here it should be `spread(events) over
   ordering` semantics.
7. **Structure**: sections, one-shot lines vs looping lines (`.bopseq` has
   `[loop]` per line and `===` sections — both proven), and clip-level
   oneshot/loop + follow action (which live in the grid model, not the
   script).
8. **References outward**: fields and points can be *invoked* from a script
   (launch/retarget a field primitive at bar 5) so script clips can
   orchestrate the spatial clip types.

## What the seeds already give us

- **`.bopseq`**: per-line breakpoint automation with loop flags, waits,
  sections, comments. Its worldview — *a line is a parameter's life over
  time* — is exactly ramp-clip semantics. Weakness for our case: no targets
  (single instrument assumed), no musical time, no randomness.
- **intermals**: compact rhythm (`1?004`), pitch/voicing as semisteps, and
  the crucial lesson that **lowercase/uppercase and single glyphs can carry a
  whole vocabulary** without parentheses. Its worldview — *dense expressive
  strings a human improvises in* — suits pattern clips.
- The tension between them is real: `.bopseq` is a *timeline* language,
  intermals is a *pattern* language. The polymorphic clip-type model (§02)
  says: don't force one grammar to be both. Let ramp clips descend from
  `.bopseq` and pattern clips descend from intermals, under one shared
  target/time model. That may be the single most useful thing to bring to
  the co-design session.

## Agent-writability test (thread requirement, worth keeping literal)

Whatever grammar emerges: an LLM must write a valid scene from the docs alone.
Practical implications — plain text, forgiving whitespace, errors as warnings
with line numbers surfaced in the clip inspector (never a silently dead clip),
and a `bopos-seq lint` that an agent can run before handing Bob a show. Add a
corpus of example clips to the repo the way `help.bopseq` documents bop.

## Address ergonomics observation

Bob flagged "how addresses are defined, and how that might relate to tracks,
needs some consideration — likely some clever solutions." The track-inherits
model (§02) is my main answer: track binds selector + prefix, lines say bare
`gain 0.8`. One more layer worth discussing: **manifest-aware names**. The
dashboard knows the loaded patch's declared params and cues; the language can
therefore resolve bare names against the manifest and *lint* unknown ones at
edit time (same philosophy as "a `/p/*` value hitting an undeclared name gets
a badge, not a guess"). Nested params (`fx/reverb/mix`) slot straight in.
