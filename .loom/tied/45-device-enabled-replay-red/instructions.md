# 45-device-enabled-replay-red

The one red test in `tools/run-tests.sh fast`:

    tests/test_device_control_routing.py
      DeviceControlRoutingTests
        .test_reappearing_physical_device_replays_persistent_enabled_state

It asserts that when a device that is **offline and persistently disabled**
heartbeats back in, the dashboard replays its `enabled 0` — i.e. a returning
device must not come back up with its output live. Observed: the frame list is
empty, nothing is sent.

## What is already known (2026-07-27)

- It is **not** a regression from the control-panel UI work. Reproduced on a
  stashed clean tree.
- It has **never passed**. `git` says the test was *added* by `cdff3a3`
  ("Promote mute safety tests", 2026-07-27) — the thread-27 promotion of the
  tied guards into `tests/`. The same commit added `ensure` and
  `ensure_device_alias` stubs to that module's `State` fake.
- It fails **standalone** as well as under `unittest discover`. An earlier note
  in `.loom/tied/4-row-regrind/decisions.md` recorded it as passing alone and
  failing only in-suite; that reading is superseded — the module-alone run
  fails too.

So the shape of the question is: the promotion carried an assertion across
from a tied guard, and either

1. **the assertion is right and the behaviour is missing** — a disabled device
   that drops off and returns really does come back with output enabled, which
   is a genuine mute/output-safety defect worth fixing in the heartbeat path;
   or
2. **the fake is wrong** — `State`/`bridge` in the promoted module doesn't
   model enough of the real heartbeat path for the replay to fire, so the test
   is asserting against a stub that can never satisfy it.

Answer that first, from the real code path (`dashboard/server.py` heartbeat
handling + the device-enabled convergence introduced by
`05-global-execution-target` / `d23bba0`), not from the fake.

## Deliverable

Either the behaviour fix plus the now-green test, or a corrected fake with a
comment naming why the original guard's setup did not survive promotion. **Do
not delete or weaken the assertion to make the suite green** — output safety on
a returning device is the kind of thing the durable suite exists to hold. If
the conclusion is that the behaviour is deliberately absent, that is a ruling
for Bob, not a quiet edit.

Verify: `tools/run-tests.sh fast` green, and the device-enabled and mute-safety
modules still green together and alone.
