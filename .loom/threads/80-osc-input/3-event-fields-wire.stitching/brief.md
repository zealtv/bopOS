# Brief: 3-event-fields-wire (bopOS, 80-osc-input)

Worktree: `/Users/bob/repos/bopOS-3-event-fields-wire`, branch `3-event-fields-wire`.
Stitch directory: `.loom/threads/80-osc-input/3-event-fields-wire.stitching/` — read its
`instructions.md` first, then the ratified design it implements:
`.loom/threads/80-osc-input/1-typed-event-fields.tied/proposal.md` (and the thread's
`instructions.md` for context and the contract-version coordination note).

Notes from the manager:

- `patches/` is gitignored except `demo-pd`/`demo-sc`. The manager copied `bonks-pd` and `kc-test`
  into this worktree's `patches/` so you can migrate them; migrate them in place here. The manager
  will carry the migrated copies into the main checkout when landing. Don't touch the main checkout.
- Contract: no other amendment has landed, so take **v1.22**.
- A sibling worker runs `6-group-name-rule` in parallel (dashboard group names, `dashboard/state.py`);
  you shouldn't overlap with it. A later stitch (`7-osc-input-port`) builds the dashboard input on
  your field validation, so keep the field checks callable (a function that checks/coerces a value
  against a declared field is worth exposing cleanly), but don't build the input.
- The dashboard fire controls and patch-editor UI are `4-event-fields-editor`, not this stitch.
  Keep the existing UI working (an event with no fields still fires).

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
