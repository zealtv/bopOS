# verification — 2-supervisor-stderr-visibility

## Ran

- **`tests/test_supervisor_errors.py`** — 9 new browser-free tests, green.
  Real child processes, not fakes, because both failures worth guarding are
  real-process behaviours. They cover: stderr reaching the buffer, the
  broadcast and the status line; the cause being the traceback's **last** line;
  a deliberate stop recording nothing; the log staying bounded; blank output
  yielding no cause rather than a blank status; cause truncation; and the
  Monitor surface (section, handler, limit, hidden-when-empty).
- **The deadlock guard is a real one.** `test_a_noisy_child_neither_blocks_nor
  _keeps_a_transcript` writes 4000 stderr lines — comfortably past the 64KiB
  pipe buffer — and asserts under an `asyncio.wait_for` timeout, so removing
  the reader thread fails the test rather than hanging the suite. It also
  asserts the tail is kept and the first line dropped.
- **Guard validity checked by reverting.** With `dashboard/server.py` stashed,
  the module fails 7 of 9 (the two survivors are the monitor.js source
  assertions, which were not reverted).
- **`./tools/run-tests.sh fast` — Ran 318 tests, OK.**
- **`tests/verify_device_control_modes.py` — 0 failures**, 16 checks. A real
  editor and a real simulation supervisor each start, run and stop clean, so
  the `PIPE` change does not disturb the normal path.
- **`tests/verify_osc_transport_monitor.py` — 0 failures**, extended (nearest
  living journey) with three live checks: the supervisor section is hidden
  until something dies, reveals itself on a `supervisor_error`, and names both
  the mode and the cause.
- **The originating incident, end to end.** Driving the real editor command
  with `--pd-bin /no/such/pd` through `launch_supervisor`, the editor status
  is now:
  `stopped unexpectedly: PdBinaryError: no usable Pure Data executable: tried
  /no/such/pd; bundles seen: /Applications/Pd-0.55-2.app/…/pd; pass --pd-bin
  to name one`, with 18 lines of traceback in the log. Previously: `stopped
  unexpectedly`, and nothing anywhere.
- Incidentally confirmed on a first attempt that happened to collide on a port:
  `stopped unexpectedly: audition: [Errno 48] Address already in use`. A
  different silent failure of the same class, now self-describing — which is
  the point of the stitch.

## Not run

- No hardware or real-Pd-GUI check. Both are outside this stitch: the editor
  path it exercises is the same one `verify_device_control_modes.py` drives
  headlessly with `--sim-no-engine`.
