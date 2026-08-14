# Verification — 0-bridge-logging

## What ran here (laptop)

- `tests/test_logpipe.py` — new, in `fast`. Four sink tests (timestamp shape,
  head-keeping cap with a discard count, uncapped run, one-generation `.prev`
  rotation) and three wiring tests read against `bash/start.sh` (`-u` on both
  services, stderr redirected, pid files still written from the service).
- `./tools/run-tests.sh fast` — **338 tests, OK** (331 before, plus the 7 new).
- `bash -n bash/start.sh`. No shellcheck on this machine.
- **Pid contract measured, not assumed.** A stand-in service launched through
  the exact start.sh idiom recorded pid `78418` in `run/io.pid`, and
  `ps -p 78418` showed the *service*, not the sink. This is why the change uses
  process substitution rather than a pipeline: `cmd | log_to … &` sets `$!` to
  the sink, and `bash/stop.sh:21` would then kill the sink and leave the bridge
  running.
- **Sink lifecycle.** `kill` on the recorded pid → sink sees EOF, writes its
  epilogue (`1961 line(s) discarded after the cap, last at …`, then
  `input closed`) and exits. Nothing is left behind, and the sink's command
  line does not match either `pkill -f` pattern in `stop.sh`.
- **Cap, live.** With `IO_LOG_MAX_BYTES=2000`, the file settled at 2092 bytes:
  head kept from `line 0`, cap notice in place, ~1961 further lines counted and
  discarded. Overshoot is the notice plus the epilogue and is bounded.
- **The real bridge, through the real idiom.** `python/io/main.py` launched via
  the start.sh line put its banner in the file at t+0.02s, and an OSC error
  line landed within a second of the event.

## What did NOT run — the stitch's own verify is a node check

The instructions ask for a create against an address with nothing on it, on a
real node, checked for legibility within a second or two. **That was not done**;
there is no rig in this session.

A laptop cannot stand in for it, and the attempt is worth recording because it
misleads: `/io/create ghost ads1115 0x4B` sent to `main.py` on macOS produced
**no output at all** — no `✗ Failed to create`, no handler line. The command
reaches the process (a subsequent reply attempt raised
`OSCClientError … Connection refused` from the OSC server, which *did* reach the
log), but the create path itself printed nothing. So this checks the plumbing —
timestamped, unbuffered, capped, correctly redirected — and leaves the *content*
of the failure case to the node.

What remains for a node, in one sitting:

1. Boot the stack; confirm `run/io.log` and `run/bopos.log` exist and carry the
   startup banners with timestamps.
2. Send `/io/create ghost ads1115 0x4B` at an empty address; confirm the failure
   is in the file within a second or two.
3. `bash/stop.sh`; confirm both services stop, no `logpipe.py` survives, and the
   next boot leaves the run behind as `run/io.log.prev`.

Item 2 is also the moment to find out why the laptop printed nothing — if the
node is silent too, that is a defect in the create path and belongs to
`3-peripheral-lifecycle`, not here.
