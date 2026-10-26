# Brief: 7-osc-input-port (bopOS, 80-osc-input)

Worktree: `/Users/bob/repos/bopOS-7-osc-input-port`, branch `7-osc-input-port`.
Stitch directory: `.loom/threads/80-osc-input/7-osc-input-port.stitching/` — read its
`instructions.md` first, then the ratified design it implements, all of it:
`.loom/threads/80-osc-input/2-dashboard-osc-input.tied/proposal.md`. Its §8 "Decided" list
overrides anything earlier in it.

What's already landed (read the `worker-result.md` of each):

- `3-event-fields-wire.tied`: typed event fields. `python/manifest.py` has
  `coerce_event_field(field, value)` (kind check and int/float coercion; it rejects out-of-range
  values, but the input must **clamp** them, so clamp before calling it or add a clamp helper
  there) and the dashboard's declared-event lookup for the active target's manifest. Reuse both.
- `6-group-name-rule.tied`: `InstallationState.valid_group_name` and the converted names; group
  names resolve to `g<id>`.

Notes from the manager:

- Put the translation logic in its own module (e.g. `dashboard/osc_input.py`) as pure functions
  that take the message, the active manifest and the groups, and return either the device-wire
  message(s) or a rejection reason. Unit-test those directly; keep the UDP listener thin.
- Contract: `3-event-fields-wire` took v1.22 for typed fields. Add the input as **v1.23**
  (§4.3, the §4 port row, §15), unless you find good reason to fold it into v1.22's entry; say
  which you did. Revise glean `external-osc-timing` with `./.glean/glean.sh` conventions (read
  `.glean/README.md`).
- The master ramp (~25 Hz, cancelled by any new master value, destination persisted at the
  start) must be testable without real time: inject a clock/scheduler.
- Rejections and clamps go into an in-memory ring of ~50 entries exposed to the dashboard state
  (the OSC tab in stitch 9 will show it; don't build the tab). If you add a websocket snapshot
  type, list it in `ws.js` `SNAPSHOT_TYPES` (glean `ws-snapshot-handlers`).
- The simfleet check: an OSC client sends to the input port of a dashboard on private ports and
  simulated nodes receive stamped events; make it a durable test or a repeatable stitch script
  like stitch 3's `verify_live.py`. The input port must be configurable for tests
  (`--input-port`, default 5552).
- A Claude worker runs `4-event-fields-editor` in parallel (dashboard JS: patch editor and fire
  controls). Stay out of the editor/fire-control JS; `git merge main` before the final run.

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
- Bob's dashboard has been stopped for this run, so the default ports are free, but two workers run in
  parallel: tests and simfleet runs should use their own/ephemeral ports, and don't leave servers
  running when you finish. No real hardware: simfleet only.
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
