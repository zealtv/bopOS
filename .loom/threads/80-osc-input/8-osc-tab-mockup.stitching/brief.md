# Brief: 8-osc-tab-mockup then 9-osc-tab (bopOS, 80-osc-input)

Worktree: `/Users/bob/repos/bopOS-9-osc-tab`, branch `9-osc-tab`.
Stitch directories: `.loom/threads/80-osc-input/8-osc-tab-mockup.stitching/` and
`.loom/threads/80-osc-input/9-osc-tab.stitching/` — read both `instructions.md` first, then
§5 "The reference tab" (and §2–3 for what it documents) of the ratified design:
`.loom/threads/80-osc-input/2-dashboard-osc-input.tied/proposal.md`.

What's already landed: read `7-osc-input-port.tied/worker-result.md`. The input lives in
`dashboard/osc_input.py`; the dashboard's public `state` snapshot carries
`osc_input: {port, recent}` (recent = last ~50 rejections and clamps: time, sender IP, address,
reason, kind). Typed event fields (`3-`, `4-` tied) and addressable group names (`6-` tied) are
also in.

## This run has two phases. Bob pre-approved the mockup, but the manager checks it first.

**Phase A — mockup (stitch 8).** Build the **OSC** tab in the running app as a working
prototype, good enough to screenshot, then stop:

- Contents per proposal §5: the dashboard's IP and the input port (copyable); the `/bop/*`
  commands with arguments; each declared event (short and explicit address, named fields with
  kinds, defaults, optional marks, ambiguity flags); each declared parameter (address, kind,
  range); groups by name and `g<id>`; recent rejections and clamps (time, sender, address,
  reason). Generated from the active target's manifest (fleet patch in Live/Simulation, the
  edited patch in Patch Edit), so it follows the mode switch.
- Use the shipped vocabulary and design language (glean `dashboard-vocabulary`; read
  `docs/` for the design-language doc it cites). Look at how the existing tabs are built and
  styled and match them; component CSS belongs to the component.
- The IP: the dashboard knows its LAN address somewhere (look for how the Remote/QR or
  header shows it); if not, compute it server-side once and expose it in state.
- Capture screenshots from the running app with Playwright on private ports, using a fixture
  project whose patch declares a mix of events (with typed and optional fields, one
  ambiguous identity) and params, two groups, and a few rejections/clamps produced by sending
  real UDP to the input port. Desktop width and a phone width (390 px). Save PNGs and a short
  `mockup.md` (what's shown, decisions, open questions) in the stitch 8 directory. Commit.
- Then end your turn with `WORKER DONE: MOCKUP READY` and wait for the manager.

**Phase B — build (stitch 9)**, after the manager replies: apply the manager's notes, finish
the tab, and verify with a `tests/verify_osc_tab.py` journey (glean `playwright-gotchas`; if
you add a websocket snapshot type, list it in `ws.js` `SNAPSHOT_TYPES` per glean
`ws-snapshot-handlers`). The journey should send real UDP to the input port and see the
rejection appear in the tab live. Run the full browser tier at the end. Write
`worker-result.md` in the stitch 9 directory.

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
`WORKER DONE: <status>` (Phase A ends with `WORKER DONE: MOCKUP READY` instead).

Note: `9-osc-tab` is claimed by the manager once 8 is tied; until then its directory is `.loom/threads/80-osc-input/9-osc-tab/` (no suffix). Write Phase B files there; the manager will move them on claim.
