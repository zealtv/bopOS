# Decisions — 0-bridge-logging

**A separate sink, not `nodelog.py`.** `python/nodelog.py` is the Bob-ratified
append-only node log (thread `42-node-logging`): a structured
`stream<TAB>values` API for callers *inside* a process, with a configurable
destination and daily files. Routing a process's stdout into it would be
exactly the widening the instructions forbid — and its cap continues into
`-N` siblings, so it is not bounded in total, which is the one property this
stitch must have. `python/logpipe.py` is a dumb stdout sink in `run/`, beside
the pid files. It borrows nodelog's timestamp shape (ISO-8601 local civil time,
offset, milliseconds) so the two files read the same way.

**Process substitution, not a pipeline.** `> >(log_to …) 2>&1 &` keeps `$!` as
the service pid. A pipeline would have quietly broken the `stop.sh` contract
the instructions told us to keep. Measured — see `verification.md`.

**Cap keeps the head, and says so in the file.** Per the 2026-08-14 amendment:
the soak's diagnosis is the onset and clustering of errors, so a tail window
throws away the useful half. At the cap the sink writes one notice, then counts
what it drops and reports the count and the time of the last dropped line when
the run ends — so the file never silently stops meaning anything.

**64 MiB default, `IO_LOG_MAX_BYTES` in `bopos.config`.** Derived, not picked:
at the 10 Hz poll rate `7-poll-timing` restored, a continuously failing
peripheral writes on the order of 2 MB/hour, so an 8-hour soak of *unbroken*
errors is ~17 MB. 64 MiB holds that whole day without ever capping, while
staying a rounding error against an SD card. The cap is the guard for a run
longer or noisier than that, not the expected operating point.

**One generation of history (`.prev`), not N.** A reboot in the middle of an
investigation should not erase the run being investigated, and two files is
enough for that. More generations is rotation policy, which is thread 42's.

**`bopos.py` had the same shape and got the same treatment** (`run/bopos.log`).
It has 76 `print(` sites, all of them going nowhere for the same two reasons.
Deliberately *not* extended past those two: `start-engine.sh` launches jackd
and Pd, whose output has different volume and different owners.
