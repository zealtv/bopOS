# 6-load-failure-followups

**Status:** part 1 complete; part 2 awaiting Bob's placement ruling
**Goal:** the "state file couldn't load" safety holds everywhere and the
operator can't miss it.

Part 1 is implemented; verification is in `verification.md`. Part 2 has a
short `placement-proposal.md` and remains unimplemented per Bob's instruction.
Leave this stitch waiting with `waiting.md` until he rules on placement.

`1` made `InstallationState.save()` raise `OSError` after a failed load and
posts a notice. Two gaps:

1. **Unguarded save.** `Dashboard.store_stopped_automation`
   (`dashboard/server.py`, ~line 1735) calls `self.state.save()` without
   catching `OSError`. In a failed-load session, stopping a live generator
   raises out of `handle_ws` and drops that browser's websocket. Every other
   save site catches and rolls back — do the same, and add a test. (An AST
   check that every `save()` call is guarded would stop this recurring.)
2. **Notice only on the Show tab.** `installation.notices` renders in Show's
   warning panel; an operator on Control or Seats sees an empty installation
   and no explanation. Propose where a load-failure notice should appear
   globally (header? every tab?) — operator-visible, so Bob rules on placement.
