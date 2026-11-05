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

**128 MiB default, `IO_LOG_MAX_BYTES` in `bopos.config`.** First derived as
64 MiB from an assumed ~2 MB/hour, then **corrected by measurement on Finn Jet**
(2026-08-14, LIS3DH pulled off the bus): the real rate is **5.7 MiB/hour**,
because a failed poll logs twice, not once. An 8-hour soak of unbroken errors is
~46 MiB. 64 MiB would still have held it, but with 1.4× headroom rather than the
4× the number was chosen for, and nothing about a soak is guaranteed to stop at
eight hours. 128 MiB is ~22 hours and still a rounding error on a card. A
*healthy* bus writes literally nothing at the same poll rate (measured: zero
bytes in 30 s), so the cap never engages in normal operation.

**One generation of history (`.prev`), not N.** A reboot in the middle of an
investigation should not erase the run being investigated, and two files is
enough for that. More generations is rotation policy, which is thread 42's.

**`bopos.py` had the same shape and got the same treatment** (`run/bopos.log`).
It has 76 `print(` sites, all of them going nowhere for the same two reasons.
Deliberately *not* extended past those two: `start-engine.sh` launches jackd
and Pd, whose output has different volume and different owners.

**Hardware verification happened here, not in a later stitch.** Bob brought
Finn Jet up mid-session, so the node check the stitch specifies was done rather
than deferred: create-at-empty-address is legible in 342 ms, the pid contract
holds against the real `stop.sh`, rotation works across a real restart, and
`bopos.py`'s boot-window `Connection refused` warnings — the Ciro Toast
symptom that motivated the stitch — are now in a file. Detail in
`verification.md`.
