# Verification — 0-bridge-logging

**Verified on hardware, Finn Jet (192.168.0.102), 2026-08-14**, at `013bdac`
pulled onto the node. The node check the stitch asked for ran; the laptop
evidence below is kept only where it measures something the node cannot.

## On the node

Stack restarted through `bash/stop.sh` + `bash/start.sh` (not `restart.sh` —
that one `sudo`s, and these services run as `pi`).

1. **Both logs exist and are timestamped.** `run/io.log` and `run/bopos.log`
   appear at boot beside the pid files, carrying the startup banners with
   ISO-8601 local time to the millisecond.
2. **The stitch's own verify case — a create at an empty address — passes.**
   `i2cdetect` showed `0x4B` empty. `/io/create ghost ads1115 0x4B` sent at
   `11:55:26.652`; the file had
   `✗ Failed to create ghost: No I2C device at address: 0x4b` at
   `11:55:26.994`. **342 ms**, against "within a second or two". On the shipped
   configuration this line reached nobody at all.
3. **The success path too**, on a real chip at `0x19`:
   `tilt: 3-axis accelerometer ready` and `✓ Created tilt (lis3dh @ 0x19)` —
   the create result that the incident notes said was "until then unknowable
   from outside".
4. **`bopos.py`'s output arrives**, including the exact class of line the Ciro
   Toast session cited: `ASSIGNED: id 0 name Seat 0 pos […]` and
   `WARNING: engine send dropped (engine not ready?): … [Errno 111] Connection
   refused` during the boot window before the engine is up.
5. **Pid contract intact, measured.** `run/io.pid` = 1341 = `main.py`;
   `run/bopos.pid` = 1340 = `bopos.py`. The two sinks are separate pids
   (1345, 1346) and match neither `pkill -f` pattern in `stop.sh`.
6. **Clean shutdown.** After `stop.sh`: no `logpipe.py` survives, both files
   end with `--- logpipe: input closed ---`, and `io.log` captured the bridge's
   own `Shutting down...` on the way out.
7. **Rotation.** The next `start.sh` left the previous run as
   `run/io.log.prev` / `run/bopos.log.prev` and began fresh files.
8. **`tests/test_logpipe.py` passes on the node's own interpreter** (Python
   3.13.5 in `~/venv`), 7 tests, not just on the laptop.

## Measured rates — these changed the default

With `tilt` created and the bus healthy: **zero bytes in 30 s** at 10 Hz. A
working installation writes nothing, so the cap only ever engages in the fault
case.

With the LIS3DH **physically pulled off the bus** (Bob, in session): **50100
bytes and 598 lines in 30 s** — 1670 B/s, **5.7 MiB/hour**, ~20 lines/s.

That is **2.9× the 2 MB/hour this stitch first derived**, because a failed poll
logs *twice*:

```
12:02:42.122+10:00 Error reading from LIS3DH at address 0x19
12:02:42.122+10:00 Error reading tilt: a bytes-like object is required, not 'float'
```

An 8-hour soak of unbroken errors is therefore ~46 MiB, not ~17 MiB — inside
the original 64 MiB cap, but with 1.4× headroom rather than the 4× assumed. The
default was **raised to 128 MiB** (~22 hours) and every statement of the rate in
`logpipe.py`, `bopos.config.example` and `python/io/README.md` now cites the
measurement rather than the estimate.

## Found on the way — belongs to `3-peripheral-lifecycle`, not here

The second line above is a **defect in the read-error path**: a failed LIS3DH
read raises `a bytes-like object is required, not 'float'` rather than
returning cleanly, and the failure is reported twice per poll. Neither is
fatal — the bridge keeps polling and recovers when the chip returns — but it
doubles the fault-case log rate and the message says nothing useful about the
bus. Recorded rather than fixed: this stitch is a redirection.

It is also the argument for the stitch, made by accident. The bug has presumably
always been there and nobody could see it, because the line went to a closed
stdout.

## Laptop evidence still worth keeping

- `./tools/run-tests.sh fast` — **338 tests, OK** (331 before, plus 7 new).
- `bash -n bash/start.sh`. No shellcheck available.
- **Cap behaviour under a forced overflow**, which the node run never reached:
  with `IO_LOG_MAX_BYTES=2000` the file settled at 2092 bytes — head kept from
  `line 0`, cap notice in place, 1961 further lines counted and reported in the
  epilogue. Overshoot is the notice plus the epilogue and is bounded.
- One misleading local result, retired by the node run: `/io/create` at an
  empty address printed **nothing at all** on macOS. The node prints correctly,
  so there is no create-path defect to hand on — it was a laptop artifact.
