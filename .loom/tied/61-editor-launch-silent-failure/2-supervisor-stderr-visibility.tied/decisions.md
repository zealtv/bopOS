# decisions — 2-supervisor-stderr-visibility

- **Precedent followed, not reinvented.** A bounded buffer, a broadcast, a
  `hidden`-when-empty section in the Monitor's System panel — the same shape as
  `osc_transport_error` / `renderTransportErrors`. New broadcast type
  `supervisor_error`; new section `Supervisor errors` directly beneath
  `Transport errors`, reusing its `.monitor-system-errors` CSS unchanged.
- **stderr only, drained by a reader thread.** `stdout` stays `DEVNULL` — it
  carries `audition.py`'s per-node info lines, which are noise here, and a
  DEVNULL'd stdout cannot deadlock. `stderr=PIPE` is drained for the child's
  whole life into a `deque(maxlen=40)`, so the pipe buffer never fills.
  Rejected: a temp file read on exit (another file to place and clean up), and
  `asyncio.create_subprocess_exec` (a larger change to a working launch path,
  against Bob's standing "fix and simplify" constraint).
- **Two bounds, deliberately different.** 40 lines per death (enough for a full
  Python traceback), 20 deaths retained. A supervisor can run for hours; this
  is a tail, not a transcript.
- **The status line gets a cause too**, not just the log: `stopped
  unexpectedly: <cause>`. The cause is the **last** non-blank stderr line —
  which for a traceback is the exception line, the explanatory one. The first
  line is `Traceback (most recent call last):`, which explains nothing. The log
  keeps the full tail regardless, so the truncated cause never loses detail.
- **A deliberate stop is silent, and structurally so.** `record_supervisor_error`
  is reached only past `supervisor_exited`'s generation guard, and
  `terminate_supervisor_process` bumps the generation and nulls `sim_process`
  *before* terminating. So a normal stop's non-zero SIGTERM return code cannot
  be reported as a failure — no return-code special-casing was needed, and a
  test pins it rather than leaving it to be re-derived.
- **`launch_supervisor`'s `except OSError` is untouched.** It was never the
  safety net it looks like — it fires only if python itself is unlaunchable —
  and this stitch covers the case it misses rather than changing it.
- Covers **Simulation as well as Patch Edit**, since both go through
  `launch_supervisor`; the entry carries `mode`, rendered as `Patch Edit` /
  `Simulation`.
