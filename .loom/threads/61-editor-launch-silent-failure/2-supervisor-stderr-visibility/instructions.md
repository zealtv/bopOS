# 2-supervisor-stderr-visibility

Stop discarding the supervisor's output. When `audition.py` dies, the operator
should be able to read why without a code-reading session.

## What ships today

`dashboard/server.py:2989-3003`:

```python
process = subprocess.Popen(command, cwd=REPO_DIR,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
```

Every traceback from the editor **and** the simulation supervisor goes to
`/dev/null`. In `61`'s originating incident the discarded text named the
missing Pd path verbatim, on the first line. What reached the operator instead
was `status: running` followed by `stopped unexpectedly` — the same two words
any crash produces, for any reason.

The `except OSError` around the `Popen` is not the safety net it looks like: it
only fires if *python itself* is unlaunchable. A supervisor that starts and then
dies takes the `launch_supervisor → True` path and reports `running` first
(`server.py:3138`).

## The change

Capture the supervisor's stderr and surface the tail of it when the process
exits non-zero, in `supervisor_exited` (`server.py:2974-2987`) — which already
knows the mode and already sets the `stopped unexpectedly` status. That status
should name a cause when one is available.

**Precedent to follow rather than invent:** the Monitor's System panel already
has exactly this shape for OSC. `osc_bridge.py:332-351` rate-limits, keeps a
bounded recent list and broadcasts `osc_transport_error`; `monitor.js:704-726`
(`renderTransportErrors`) renders a timestamped, hidden-when-empty log with a
count. Match that — a bounded buffer, a broadcast, a `hidden` section in the
System panel — instead of a second unrelated mechanism. Whether the editor
status line gets a short cause in addition is an implementation call; the log
is the load-bearing half.

Two things to get right:

- **Don't deadlock.** `stderr=PIPE` with nobody draining it blocks the child
  once the pipe buffer fills, and `audition.py` prints per-engine lines on
  stdout at `:247` for the life of the session. Drain it (a reader thread, or
  `asyncio.create_subprocess_exec`), or write to a temp file and read the tail
  on exit. Do not leave an undrained `PIPE`.
- **Bound it.** A supervisor can run for hours. Keep a tail, not a transcript.

## Verify

- A browser-free test in `tests/`: launch a supervisor command that exits
  non-zero with a known string on stderr, assert the string reaches the
  captured buffer and that `supervisor_exited` records a cause.
- A long-running noisy child does not block — the deadlock is the failure this
  stitch can most easily introduce, and it would present as the editor hanging
  rather than crashing, which is worse than what we started with.
- Sanity: a normal editor session still starts, runs and stops clean.

## Why this is worth its own stitch

`1-pd-binary-resolution` fixes one cause. This fixes the *class*: the next
silent supervisor death — a missing python dep, a port collision, a bad
manifest reaching `audition.py` — becomes one readable line instead of another
session spent reading `server.py`. It covers Simulation as well as Patch Edit,
since both go through `launch_supervisor`.
