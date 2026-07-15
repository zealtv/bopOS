# Handoff — accepted tabs next sweep, simulation coherence first (2026-07-15)

State at handoff: tabs-0/1/2 are tied; Bob accepted the independent UX review's
correctness-first next sweep with one amendment: **production points remain
runtime-only and do not persist with venues**. That follow-up is dropped. Loom
has 97 tied stitches, 6 dropped stitches, no claim, and one loose end:
`ui-tabs/tabs-3-next-sweep/01-simulation-transition-coherence`.

## Start the next session here

1. Read `CLAUDE.md`, this handoff,
   `.loom/tied/tabs-2-review-session/{results.md,code-diagnosis.md,bob-next-sweep-ruling.md}`,
   and the 01 instructions; run `./.loom/loom.sh status`.
2. Claim only `01-simulation-transition-coherence`.
3. Fix late updates for removed virtual uids and prove Simulation/Patch edit →
   Live clears virtual cards and restores the correct live target, seat
   assignments, master and mute without browser refresh.
4. Add a focused rapid-transition regression against the real dashboard and
   managed audition runtime. Tie 01 before resuming 02.

## Accepted later sequence

- 02 bounded patch-switch terminal state;
- 03 hostname/seat leaks and seat-based Dashboard labels;
- 05 global Live fleet / Simulation / Patch edit target control;
- 06 Seat/Device boundary + unbound UID-admin design gate;
- 07–14 the accepted workspace, content, live-control and identity follow-ups.

The exact accepted plan is
`.loom/tied/tabs-2-review-session/next-sweep-proposal.md`. The full independent
review is lore item `2026-07-15-dashboard-tabs-hands-on-expert-review`.

## Launch and worktree

- Host disk space was critically low at handoff (about 34 MiB free). Free space
  before browser-, screenshot-, or test-heavy work to avoid misleading failures.
- Dashboard process from the prior handoff remains on port 8080; static files
  are served live, but confirm the process in-session before relying on it.
- No `.pd` file was edited.
- The handoff commit is the current HEAD; the worktree should be clean.
