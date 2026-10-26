# Brief: 6-group-name-rule (bopOS, 80-osc-input)

Worktree: `/Users/bob/repos/bopOS-6-group-name-rule`, branch `6-group-name-rule`.
Stitch directory: `.loom/threads/80-osc-input/6-group-name-rule.stitching/` — read its
`instructions.md` first, then §2 "Targets" of the ratified design:
`.loom/threads/80-osc-input/2-dashboard-osc-input.tied/proposal.md`.

Notes from the manager:

- Start from `dashboard/state.py` `clean_group`, `adopt_group_names` and
  `group_name_adoption_notice`. Put the rule in one function (e.g. a validator plus a
  converter) that the later OSC input stitch can reuse to resolve names.
- The group editor in the dashboard UI must enforce the rule too (client-side feedback, with the
  server as the authority). Read glean `dashboard-vocabulary` and `playwright-gotchas`; add or
  extend a `tests/verify_*.py` journey if the editor behaviour changes visibly.
- Conversion on load: lowercase, other characters to `_`, suffix on clash, and the existing notice.
  Make sure an all-digits name, `g12`, `all`, `bop` and the plane names convert to something legal
  too (choose a clear, deterministic rule and note it).
- A sibling worker runs `3-event-fields-wire` in parallel (manifest, node, osc_bridge fire_event);
  you shouldn't overlap with it.
- No contract change is needed for this stitch alone (the input stitch documents group-name
  targets), unless you find the contract already describes group names — then note it.

**Usage:** you can't see your own usage, so the manager watches it and will message you if you must
pause. Then stop at your last clean commit, write `worker-result.md` starting **PAUSED CLEANLY**
with a "where I stopped" note, commit it, and end with `WORKER DONE: PAUSED CLEANLY`.

## How this run works (read before starting)

You are a worker. A manager session (Claude Opus, in another tmux pane) dispatched this stitch, reviews
your diff, and lands it on main. Bob is the project owner and isn't watching; don't wait on him.

- Read `CLAUDE.md`, then `.glean/findings/INDEX.md`; open the findings relevant to this stitch
  (always: `verification`, `never-edit-pd`, `hardware-claims`, `osc-contract`, `horizon-refactor`,
  `zero-indexing`, `pd-float-precision`, `commit-style`).
- Work only inside this worktree, on its branch. Commit in small, reviewable commits as you go
  (plain-prose subject, body says why), ending each message with your own co-author line.
- **Don't touch loom lifecycle state** (no `loom.sh claim/tie/drop/queue/new/anchor/wait`); the manager
  owns it. You may write files inside your stitch's directory.
- **Don't run `codex-usage` or `claude-usage`.** The manager tracks usage.
- **Never edit a `.pd` file.** If Pd needs a change, write it down in `worker-result.md`.
- **Bob's live dashboard is running** from the main checkout (`dashboard/server.py`, UDP 5550/5551,
  TCP 8080). Don't stop it, don't send to it, and don't bind those ports in ad-hoc runs; tests and
  simfleet runs must use their own/ephemeral ports. No real hardware: simfleet only.
- Tests: `./tools/run-tests.sh fast` from the venv (`~/.venvs/bopos`) while iterating, plus
  `./tools/run-tests.sh browser` if you touched dashboard UI. UDP binds may need a run outside the
  sandbox: ask for escalation rather than skipping them.
- Before the final test run: `git merge main` (the manager may have landed other work).
- Add no new feature beyond the stitch's instructions. If an instruction is ambiguous or seems
  wrong, choose the reading closest to the ratified proposal, note the choice in `worker-result.md`,
  and carry on; stop and ask (BLOCKED) only when a choice would be hard to undo.

## When finished

Write `worker-result.md` in the stitch directory, starting with exactly one of
**READY FOR REVIEW**, **PAUSED CLEANLY** or **BLOCKED** (with the question), then: what changed
(by file), decisions taken and why, tests added, the test result (tail of the output), and anything
the reviewer should look at hardest. Commit it, then end your turn with one line:
`WORKER DONE: <status>`.
