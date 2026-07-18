# 8-docs-and-handoff

Close the slice. Requires stitches 1–7 tied.

Scope:

- `dashboard/README.md`: document the Show tab (naming, steps/sections/
  messages, playback semantics summary, show-file location and schema
  pointer, consoles and filter syntax).
- Root `README.md`: mention the Show tab where tabs are listed, if they are.
- `CLAUDE.md`: update the thread-ordering section — record the 14-show-tab
  slice as complete, the Show naming (Sequencer tab is gone), and that
  `patch-workflow-friction/friction-0..1` resumes as next; note what stays
  gated (scene language, curves, point motion, musical time).
- Confirm `tools/simfleet.py` gained whatever this thread needed (it should
  have happened in-stitch; audit, don't duplicate).
- Write `.notes/handoff-2026-07-18-show-tab.md`: what shipped, verify
  scripts and how to run them, deferred items (musical time, curves, point
  motion, visualisation view, multi-column), and open §08 decisions the
  co-design still owns.
- Simulator/audition config compatibility note if anything changed.

Verify: docs accurate against the shipped behavior (spot-check claims by
running one existing verify script); no stale "Sequencer" references left
(`grep -ri sequencer` over dashboard/, docs/, README).
