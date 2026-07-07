# node-contract-fixes — design decisions (2026-07-07)

Decisions made before delegating the build; the governing rule is contract §1:
*a node never crashes or falls silent for lacking hardware.*

## 1. I2C degrade (`python/io/sys_i2c.py`, `python/io/main.py`)

- `smbus2` import becomes optional (`HAVE_SMBUS` flag): a box without the
  package (dev laptop) must still run the io bridge.
- `scan_bus()` opens `SMBus(bus)` inside a try; any `OSError` on open (no
  `/dev/i2c-N`, permissions, no smbus2) → return `[]`. Empty scan is the legal
  answer, mirroring `sys_wireless.read_wireless`'s `(None, None)`.
- New `have_bus(bus=1)`: `/dev/i2c-<bus>` exists **or** `BLINKA_MCP2221` env is
  set (laptop USB adapter — peripherals there go through blinka/busio, not
  smbus2, so the device node check alone would false-negative).
- `/io/create` when `have_bus()` is false → reply `/io/error <name> no-bus`
  (contract §11 verbatim). Other create failures reply
  `/io/error <name> create-failed` — same shape, fail loud instead of
  print-only. Contract names only `no-bus`; `create-failed` is the same
  message shape applied to the adjacent failure, not a new verb.

## 2. Identity discovery (`bash/start.sh`)

- Primary interface = `ip route get 1.1.1.1` device; fallback: first non-lo
  interface with `operstate == up`; fallback: first non-lo interface; final
  fallback MAC string `unknown` (helper.py then simply finds no match and the
  node stays unassigned-and-announcing — contract §5's legal state).
- `/home/pi` hardcodes replaced by deriving `BOPOS_DIR` from the script's own
  location (pattern already used by `start-laptop.sh`) and `$HOME/venv` with a
  `python3` fallback when no venv exists.

## 3. Targeted process management (`stop.sh`, `helper.py`, `/os/restart-engine`)

- start.sh writes pidfiles to `$BOPOS_DIR/run/` (gitignored): `helper.pid`,
  `io.pid`; engine start moves to a new `bash/start-engine.sh` (jack + PD +
  patch start script, fresh RANDOM/dates, re-reads active patch) which writes
  `jackd.pid`/`pd.pid`. The interactive "press key to skip" waits are guarded
  with `[ -t 0 ]` so the script also runs headless.
- New `bash/stop-engine.sh`: kill pd + jackd from pidfiles, fallback
  `pkill -x pd` / `pkill -x jackd` (exact process names — the offender was
  `pkill python`, which killed helper/io/everything).
- `stop.sh` = stop-engine.sh + pidfile kills for helper/io, fallback
  `pkill -f` on the exact entrypoint paths. `pkill python` is retired
  (contract §7). Same treatment for `stop-laptop.sh`; `start-laptop.sh`
  launches io/main.py by full path so it is pkill-f-targetable.
- `helper.py` `/patch` handler calls stop-engine.sh instead of
  `pkill pd; pkill jackd`.
- **`/os/restart-engine`** (contract §7) lands as helper.py handler
  `/restart-engine`: reply to PD (→ wire `/rpt <id> helper-reply
  restart-engine`), then stop-engine.sh + start-engine.sh via Popen (detached;
  helper's serve loop must not block on jack's settle time).
  Wire transport today is `helper restart-engine`, which needs a one-line PD
  route addition — spec written to `../pd-edits-for-bob.md`, Python side does
  not wait (2026-07-07: Bob confirmed he's happy to edit PD patches; strict
  backwards compatibility de-prioritized).
- simfleet learns `helper restart-engine` → `helper-reply restart-engine`
  (tracking rule from dashboard-0-sim-fleet).
