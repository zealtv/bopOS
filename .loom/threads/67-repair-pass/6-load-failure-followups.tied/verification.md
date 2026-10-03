# Part 1 verification — 2026-10-03

`store_stopped_automation` snapshots Seat and Device parameter mirrors before
estimating held values. On `OSError`, `TypeError` or `ValueError` from save,
it restores the mirrors, including previously absent maps, without replacing
shared editor dictionaries, then propagates the failure to its caller.
The live Stop WebSocket handler catches that failure and reports the existing
error message type before sending any command or changing automation state.

Regression coverage:

- Real malformed installation file: a group Stop restores both Seats,
  physical and simulated Device mirrors, preserves automation and original
  file bytes, sends no command/broadcast, and returns an error normally. A
  subsequent request on the same WebSocket still succeeds.
- All three save exception types restore the editor's shared params object
  in place. The existing successful held-value persistence test remains green.
- Small AST check: every direct `self.state.save()` call in `dashboard/server.py`
  must be in a try body with an OSError-capable handler, before crossing a
  function boundary. Calls in a try's handlers/else/finally do not count as
  guarded by that try. This is a source guard, not proof of rollback semantics;
  the behavior tests cover rollback.

Verification: `tools/run-tests.sh fast` passed **346 tests**; focused
`tests/verify_generator_drawer.py` passed all agreeing/mixed target checks,
including live Stop and generator state. Complete logs accompany this record.
Whitespace check passed. Software/simfleet only; no Pi/audio claim.

## Part 2 verification — 2026-10-03

Bob approved option 2 in ruling.md and resumed the stitch. That waiting gate
is resolved. One shared renderer subscribes to replayable state snapshots and
renders the existing installation.notices as text in a persistent status
region outside all main tab panels, directly below the tab bar. Standalone
Remote mounts it directly below the header. Empty notices hide the region;
there is no dismiss, repair or overwrite control. Show renders only its own
warnings, so the installation notice is not duplicated there.

The notice's measured height is deducted from Control's existing viewport-height
column layout, including when paths wrap; Remote uses normal document flow.
No file-repair behavior or backend state handling changed.

Passed:

- `./tools/run-tests.sh fast`: **356 tests, OK** (`ui-fast.log`).
- `tests/verify_state_load_safety.py`: all checks pass (`ui-load-safety.log`).
  Real failed-load and repaired-load sessions cover every main tab, including
  Control and Seats, plus standalone Remote. The journey checks one status
  region, readable existing text/filename, exact placement outside tab panels,
  no action controls, no duplicate Show warning, reload persistence, and absence
  after a healthy load. It retains original-byte preservation, rejected-venue,
  save-refusal and successful repaired-save checks. Page errors from both
  documents are collected; none occurred.
- `tests/verify_show_targets.py`: **0 failures** (`ui-show-targets.log`), including
  missing-target warnings at Show load and authoring time.
- `tests/verify_control_tab.py`: passed (`ui-verify_control_tab.log`), including
  standalone Remote cards and no page errors.
- `tests/verify_control_column_scroll.py`: passed (`ui-verify_control_column_scroll.log`),
  including Control column scroll and Remote document scroll.
- `node --check dashboard/static/js/installation-notice.js` and whitespace check:
  passed.

Screenshots `notice-control.png`, `notice-seats.png`, and `notice-remote.png`
were visually reviewed. The notice is readable, wraps at tablet width and sits
in the approved placement. Browser checks used isolated local fixtures; no
Pi, audio or Pd claim. Both parts are complete; this stitch can be tied.
