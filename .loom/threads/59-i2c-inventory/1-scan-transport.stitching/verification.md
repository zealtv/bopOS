# Verification — 59/1 IO control path

2026-10-04. Implemented against ratified proposal §8a; software verified.
No commit and no loom claim/tie performed, as directed by the task brief.

## Software results

- `./tools/run-tests.sh fast`: **461 tests, OK**, review run 11.827 s. Includes
  13 bridge tests and 15 IO control tests, plus contract-version agreement,
  node administration, OSC transport, dashboard state and existing regressions.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest discover -s tests -p test_io_bridge.py`:
  **13 tests, OK** (initial focused pass; subsequent changes included in final fast run).
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest discover -s tests -p test_io_control.py`:
  **15 tests, OK**, review run. Missing scan/write receipts advance node FIFO
  without replies; stale timer callbacks cannot drop the next job. Dashboard
  scan/write deadlines produce internal timeout state, not wire error tokens.
  Receipts, replacement and shutdown cancel timers.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/verify_io_control.py`:
  **PASS**, both journeys, rerun after review changes. Moved from the stitch
  directory into `tests/` so `tools/run-tests.sh browser` discovers it.
  Real pyOSC3 bridge/node helpers and UDP sockets exercise FIFO scans/writes,
  dual replies and error relay, with chip access faked. Real dashboard/server.py
  and tools/simfleet.py subprocesses on isolated non-default ports exercise two
  unassigned exact UIDs, sorted address/claimed facts, writes, errors and initial
  WebSocket snapshots after reconnect. No production daemon, engine or Pi runs.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/verify_log_destination.py`:
  **5 checks PASS, 0 failures**, existing Device logging browser regression.
  No new UI is implemented; Device inventory remains stitch 2.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile python/io_control.py python/bopos.py dashboard/osc_bridge.py dashboard/server.py tests/test_io_control.py tests/verify_io_control.py`:
  **PASS**, all Python files changed in review (other original files compiled previously).
- `git diff --check`: **PASS**.

The socket/browser commands initially encountered sandbox socket restrictions;
they passed when rerun with the required approval. The first new control-test
run found two fixture expectations (OSC traffic broadcasts and sorted fake
addresses); those were corrected and pass in the final fast run. Extending the
integration verifier briefly introduced a syntax error, corrected before its
successful final run. No remaining failing checks.

## Decisions and boundaries

Admin inventory uses fixed bus 1, matching ratified §8a and the drivers. The
existing engine optional scan bus argument remains available; the IO object
describes bus 1. A bus must be openable to be usable, so missing SMBus support,
missing device or failed bus open reports `bus:null`. `scanned` records that a
scan ran, including an unavailable-bus attempt; absence is distinguished by
`bus:null`. Only the bridge scans, under the existing shared IO lock, reporting
live peripheral addresses without probing them. Kernel EBUSY preserves `claimed`.

`io-modules` is absent. `/io/registry` carries the same complete IO object as
`/io/scanned`; successful driver returns produce `/io/written`. The node stores
IO facts, queues one outstanding scan and one outstanding write independently,
and advances on terminal local receipts or a 3-second deadline. No value bundles go to 7771 or
the LAN. Stream leases, 5551 reception, manifest ownership, module UI and
Performance enforcement belong to later stitches.

The local grammar has no request IDs or timeout reason. After 3 seconds
(`BRIDGE_REPLY_TIMEOUT_SECONDS`) without a receipt, the node drops that request
and starts the next queued request of that kind. It emits no timeout reply or
new wire token. The dashboard clears its pending state after 4 seconds
(`IO_REQUEST_TIMEOUT_SECONDS`), records `status:err, phase:timeout` internally,
broadcasts the device state and refreshes its report. Observed IO facts are
retained. Timers are cancelled on receipts and shutdown; dashboard replacement
also cancels the previous pending timer. Driver command semantics remain with
the existing drivers (a successful return acknowledges dispatch).

## Pending — real hardware adoption

**NOT RUN; no Pi/I2C/audio/LAN adoption claimed.** On Finn Jet or the intended rig:

- Verify startup ordering and localhost replies on real 6662/7771 alongside
  bopos.py sending commands on 8880; confirm engine value bundles still arrive.
- Scan an empty bus, no/unopenable bus, live registered peripherals and a
  kernel-owned address; confirm no contention and truthful inventory/UU flags.
- Verify real create/import/setup errors, invalid arguments, unknown targets,
  raised writes and successful writes, including recovery and driver versions.
- Confirm dashboard receives exact-device receipts and unsolicited errors on
  installation-LAN 5550. Loopback tests do not prove broadcast on a real LAN.
- Perform the existing hardening stitch's pending wrong-address LIS3DH check.

No `.pd` changes were made. Real Pd reception and audible behavior remain Bob's
hardware checks; the Python/OSC checks above use fake peripherals and an OSC
engine sink only.
