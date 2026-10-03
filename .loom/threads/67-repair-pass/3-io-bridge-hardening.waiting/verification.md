# Verification — 3-io-bridge-hardening

2026-10-03. Software half verified; hardware and wire decisions remain pending.

## Passed, without browsers or hardware

- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest discover -s tests -p test_io_bridge.py`: **10 tests, OK**, `software.log`.
- `./tools/run-tests.sh fast`: **356 tests, OK**, `fast.log`.
- `git diff --check`: passed.

The tests instantiate the real manager with a mocked OSC client and mocked
peripheral modules; no sockets, Pi, Pd, browser, or I2C device is needed.
They pin reserved names and management-verb precedence, peripheral command
forwarding, the one-address-segment guard, empty commands/bare IO/unknown verbs,
create no-bus and existing create-failed replies, invalid address/rate/bus
containment, unchanged poll rate after invalid input, scan's registered-address
skip list, cleanup-before-replacement, cleanup after failed setup, and retention
of the old instance for an invalid type.

An event-coordinated read blocks while a second thread attempts a write, scan,
or replacement. Each operation stays blocked until the read exits, then runs.
One manager-wide reentrant lock serializes registry access and chip operations,
including setup/cleanup and two names sharing a chip. Shutdown stops the server
thread before acquiring the same lock for cleanup.

LIS3DH tests show that default 0x19 and explicit 0x18/0x4B reach the driver as
`address=...`, that the wrapper retains that address for scan, and that a driver
setup exception propagates. This is **not** proof of wrong-address behavior on
Finn Jet. The manufacturer's [driver source](https://github.com/CoreElectronics/CE-PiicoDev-Accelerometer-LIS3DH-MicroPython-Module/blob/main/PiicoDev_LIS3DH.py)
confirms the address keyword; the node's installed version remains part of the
hardware check.

## Pending — Bob's Finn Jet hardware claim

**NOT RUN.** Confirm an empty/wrong address on Finn Jet, create a LIS3DH there,
and observe an error rather than successful registration or zeros. Record the
node revision, installed driver version, actual/incorrect addresses, io.log and
engine reply. Verify correct-address creation and `/io/scan` still work. This
check belongs to Bob; the stitch is `.waiting`, not tied.

## Pending — wire ratification

See `wire-proposal.md`. Contract v1.18 explicitly documents `no-bus` only;
existing `create-failed` is preserved for existing creation failures. No new
reason token, bridge error-name convention, or reply shape was implemented.
Malformed arguments and unknown dispatch/write failures are diagnostic in
io.log; their proposed OSC replies remain open. Thus the stitch's original
"no branch silent" criterion is met at the log level, **not** as an OSC-reply
claim for every failure. The missing wire behavior is explicitly deferred.

No OSC contract, Pd files, transport/ownership design, read-error duplication,
or unplug/replug recovery changes. No browser tier needed for these Python-only
IO changes.
