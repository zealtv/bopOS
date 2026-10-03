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

Part 2 is deliberately unimplemented. `placement-proposal.md` gives three
options and recommends a persistent strip below the tab bar, plus below the
Remote header. Per Bob's explicit instruction, this stitch remains waiting
for his placement ruling; it is not tied. Unrelated working-tree edits remain
outside the commit.
