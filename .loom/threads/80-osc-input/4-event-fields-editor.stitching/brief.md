# Brief: 4-event-fields-editor (bopOS, 80-osc-input)

Worktree: `/Users/bob/repos/bopOS-4-event-fields-editor`, branch `4-event-fields-editor`.
Stitch directory: `.loom/threads/80-osc-input/4-event-fields-editor.stitching/` — read its
`instructions.md` first, then the ratified design: `.loom/threads/80-osc-input/1-typed-event-fields.tied/proposal.md`
(§1 manifest, §5 the patch editor and fire-control rows).

What's already landed (read `3-event-fields-wire.tied/worker-result.md` and its reviews):

- `python/manifest.py` validates event `fields` (0–16; a field is a param declaration without
  `path`/`dashboard`, plus `optional`; optional fields trail and carry a default) and rejects
  `arity`/`defaults` loudly. `coerce_event_field` checks a value against a field.
- The dashboard fire path tags values by declared kind. The UI still reads `arity`/`defaults`
  (`dashboard/static/js/control-surface.js`, `dashboard/static/js/dashboard-patches.js`), so the
  patch editor currently writes manifests the validator rejects, and fire controls show no
  inputs for fielded events. Fixing that is this stitch. The stitch 3 result names the browser
  journeys that fail until you do; they must all pass when you finish.

Notes from the manager:

- Patch editor: an event's field list edited exactly like the param list (reuse the param row
  code and its kind controls rather than writing a second editor): name, kind, range/options,
  default, an "optional" checkbox. Add/remove/reorder as the param list allows. No `arity` left
  anywhere in the UI.
- Fire controls (control surface and Show/`show.js` wherever events fire): one control per field,
  the same control params use for that kind, labelled by field name, prefilled from the default.
  Text fields: a text box; respect the wire limits (printable ASCII, no whitespace, 1–255).
- Use the shipped vocabulary (glean `dashboard-vocabulary`); keep the look of existing rows.
- Verify with a `tests/verify_*.py` journey that authors an event with mixed fields, saves it,
  reloads it, and fires it with values, checking what the server receives (glean
  `playwright-gotchas`; journeys run a real dashboard on private ports, see
  `tests/verify_group_names.py` for a recent example). Run the full browser tier at the end.
- A Codex worker runs `7-osc-input-port` in parallel (server-side input on UDP 5552, mostly
  Python). Stay out of `dashboard/osc_input*` and its tests; `git merge main` before the final run.

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
