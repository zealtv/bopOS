# p8 docs and handoff worklog

## Outcome

- Rewrote the Dashboard operator reference for exclusive Show playback,
  progress/armed state, global transport, persisted all-cue lead, bounded
  scrollbox, direct drag arrangement, keyboard editing, and global undo.
- Reconciled the base Show design/schema with its p2/p3/p4/p5/p6 amendments:
  canonical examples no longer carry retired `forward_sync` or empty
  then-actions, concurrent-play wording is superseded, and current transport,
  cue scheduling, scrollbox, inspector, drag, and undo behavior reads as one
  document.
- Marked `15-show-polish` complete in `CLAUDE.md`. The newer ratified ordering
  remains authoritative: `automation-2-show-builder-gui` is next, and the
  host-loom `patch-workflow-friction` close-out resumes after thread 16.
- Replaced the planning-era Show-polish handoff with the shipped state,
  commits, verifier inventory, amendments, deferred work, and next action.
- OSC contract §8 already contained p7's additive legacy-group/promotion
  amendment, so p8 did not duplicate it. No `.pd` files changed.

## Verification

All 16 retained Show verifiers passed on HEAD (nine thread-14 scripts plus
p1–p7). Aggregate reported counts where scripts expose them include 93/93 for
the p7/polish half; every script exited 0. Browser verifies used the real
dashboard on random loopback ports with headless Chromium.

The tied `5b-compact-rows` verifier was amended because its old whole-page
“20 rows fit unscrolled” assertion was superseded by p4's deliberate bounded
scrollbox. Its replacement retains the compact-row ≤40 px budget and proves
the 20 rows overflow inside the ≤500 px list box without scrolling the page;
the amended verifier passed 12/12.

Terminology and behavior sweeps:

- stale canonical `forward_sync`, concurrent-step, implicit-empty-stop, fixed
  cue-lead, and old global-transport wording removed; only the intentional
  legacy-load amendment remains.
- `facilitator` under dashboard static assets remains only in route/file/code
  identifiers and the defensive legacy manifest strip, not rendered Patch-tab
  terminology.
- `git diff --check` passed. Documentation claims were spot-checked against
  `show.js`, current CSS, and the focused running-app verifiers.

No hardware, iPad/touch-device, audio, or audible PD verification was run.
Verifier-regenerated screenshots were restored rather than committed. Bob's
untracked `dashboard/shows/` remains untouched.
