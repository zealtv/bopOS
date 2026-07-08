# scene-sequencing

**Goal:** bopOS-native sequencing of the fleet — scenes authored in a simple scripting
language, launched from a trigger-slot UI, replacing the Ableton + Max for Live approach
that made Belief System unreliable. Context: review §10.

Design targets:
- **Scene scripting language**: scenes are text scripts that can be **triggered, mixed,
  or crossfaded**. Features: loops (looping sequences), one-shot lines, LFOs,
  "note"/random-number generation, rhythm notation.
- **Study the existing seeds before inventing syntax:**
  - bop's `.bopseq` (`pd/bop/sequences/help.bopseq`, `example.bopseq`): per-line
    `param [loop] v1 t1 v2 t2 …` breakpoint automation, `- <ms>` waits, `===` section
    breaks, `--- comment;`, bare midi-note lines. Read the bop help patches
    (`pd/bop/help-bop.sequence.pd` et al.) for how bop notates parameters.
  - Bob's **intermals notation** (https://zeal.co/notebook/intermals/): semisteps chord
    voicing (float `0.43` = root + maj3 + min3), string/fret via semisteps, bitplucking
    envelope digits (`7965`), symbolic text language (`@` root, `=` tuning, `>` fret,
    lowercase = intermals like `p` pluck / `b` bow, uppercase = signals like `G` gain),
    rhythm/time as `1?004` (quarter note).
- **Trigger-slot UI** (Ableton session-view pattern): a grid of scene slots launched
  across time; belongs in the dashboard (and a simplified version in the facilitator
  view). A scene targets the fleet: per-device, groups, or `/all`.
- **Agent-coded composition is a first-class workflow**: an artist should be able to
  prompt a sketch *and* the control patterns across many instances into place. Design
  the language to be easy for an LLM to read/write (plain text, forgiving grammar,
  documented by example) and keep scenes as files in a git-friendly layout.
- **Where it runs:** the dashboard backend is the natural sequencer host (it has the
  clock leadership, positions, and the UI); standalone-app remains the fallback if the
  dashboard becomes a liability. Scene playback must use `clock-sync` cues for anything
  time-tight.

Suggested path: (1) spec the language on paper against 2–3 real scenes from past works;
(2) prototype the interpreter in the dashboard backend driving `/gain`-level params;
(3) trigger-slot UI; (4) crossfade/mix semantics between scenes.

Child `video-mask` holds the video-as-parameter-mask idea (unresolved home).

---
**2026-07-08 (Bob): thread PAUSED until the rest of the foundation is in place**
(clock-sync, spatial-audio Stage A, audition rig). Both children are `.waiting`:
`scene-language-spec` on the co-design session with Bob (his brief is in the
stitch — never spec solo), `video-mask` on spatial Stage A + the language
existing. Autonomous sessions: do not claim anything here; unpause is Bob's call.
