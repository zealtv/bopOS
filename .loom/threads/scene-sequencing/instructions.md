# scene-sequencing

**Goal:** bopOS-native sequencing of the fleet — scenes in a simple text
language, launched from a clip-grid UI — replacing the Ableton + Max for Live
setup that made Belief System unreliable. Context: architecture review §10.

**Status:** **paused by Bob (2026-07-08).** All children wait on a co-design
session with Bob. Autonomous sessions: don't claim anything here; unpausing is
Bob's call.

The pause was "until the foundation is in place" (clock sync, spatial audio,
audition rig) — that software is now built. Since then the **Show tab** shipped
(steps, sections, then-actions, parameter automation, presets, events), which
covers part of this ground. Worth raising with Bob when he next plans work.

## Stitches (all waiting on Bob)

- `show-lanes-and-scenes-design` — next Show model: lanes of steps, scene rows,
  follow actions (Ableton Session View + QLab as references).
- `scene-language-spec` — the text language. Bob's brief is in
  `bob-design-notes-2026-07-08.md` inside it. **Never spec solo.**
- `video-mask` — video as a spatial parameter mask. May be made unnecessary by
  node-side spatial primitives in the language.

## Design targets (for the co-design session)

- **Language:** scenes are text that can be triggered, mixed or crossfaded;
  loops, one-shots, LFOs, note/random generation, rhythm notation.
- **Seeds to study first:** bop's `.bopseq` (`pd/bop/sequences/`), and Bob's
  intermals notation (https://zeal.co/notebook/intermals/).
- **Clip-grid UI** on the dashboard (simpler on Remote); scenes target all /
  groups / Seats.
- **Agent-writable:** plain text, forgiving grammar, documented by example,
  scenes as files in git.
- **Runs in the dashboard backend** (clock leader); time-tight playback uses
  synced events.
