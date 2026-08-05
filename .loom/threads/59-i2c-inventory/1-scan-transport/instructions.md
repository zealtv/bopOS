# 1-scan-transport

Get the connected-I2C-address list from a physical device to the dashboard,
and write the contract amendment that describes it.

## Decide

Three candidate paths, in rough order of preference:

1. **`bopos.py` scans, answering `/all/os/to <uid> probe i2c`** →
   `/os/probe <id> i2c <addr>…`. `bopos.py` already imports `sys_i2c` and the
   reply shape exists. Cost: `/os/probe` currently only *reads held values*
   (`python/bopos.py:1554-1571`), so this widens the verb from "report what I
   already know" to "go and look" — say so explicitly in the amendment rather
   than sliding it in. Also: `bopos.py` cannot see the io bridge's peripheral
   registry, so `skip` is empty and the probe touches addresses the poll loop
   owns.
2. **`bopos.py` relays to the io bridge on 8880** and the bridge replies to
   `bopos.py` rather than to the engine's 6662. Correct `skip`, but it adds a
   localhost request/reply leg with a timeout, a second reply destination for
   `/io/scan`, and a dependency on the bridge being up.
3. **An `i2c` array in the `/os/report` JSON.** Cheapest UI, no new verb, but
   the scan then runs on every report — including the on-connect report sweep
   — for a fact that changes only when someone plugs something in.

Whichever wins, resolve these before implementing:

- **Bus contention.** Does probing an address a peripheral is mid-transaction
  on actually disturb it? Measure on the rig with a live MPR121 or ADS1x15
  (`python/io/` has both) rather than reasoning about it. If it does, option 1
  is not viable as written and the answer is 2 — that is the finding this
  stitch exists to produce.
- **No bus at all.** `sys_i2c.have_bus()` is false on a device with I2C
  disabled and on the laptop rig unless `BLINKA_MCP2221` is set;
  `scan_bus` also returns `[]` when `smbus2` is missing. "No bus" and "bus
  present, nothing on it" are different operator facts and must stay
  distinguishable — `has_i2c` already carries the first, so do not let an
  empty address list mean both.
- **Bus number.** `/io/scan` takes an optional bus argument defaulting to 1.
  Decide whether the fleet surface takes one or is fixed at bus 1, and say
  why.

## Deliver

- The chosen path implemented in `python/bopos.py` (and `python/io/main.py`
  if option 2 wins).
- A contract amendment in `docs/OSC-CONTRACT.md` — additive, with a §15
  revision-history entry, at whatever version is current when this lands.
- Simfleet parity in the same stitch, per the standing rule that new protocol
  features land in the simulator alongside: `tools/simfleet.py:480` already
  answers `"has_i2c": False`, so give it a configurable fake address list so
  `2-device-tab-inventory` has something to render headlessly.
- A durable check in `tests/` on the code surface that owns it.

## Gate

The OSC contract is Bob's to ratify. Write the proposal (options, the
measured contention finding, the recommendation) into this stitch, mark it
`.waiting`, and surface it — the amendment is small but it is still the wire.

## Update 2026-08-05 — the pd-side scan path is now proven, and still not stale

The sibling `6-io-create-dropped` warned that `scan` had no outlet on
`bopos~.pd`'s `[route report create poll]` and so fell into the generic
branch. That premise is **retired**: the generic branch now prefixes with
`set io $1` (commit `bd2d989`), so a patch sending `scan 1` reaches the bridge
as `/io/scan 1` correctly, and Bob's reboot confirmed the whole io path live.
That sibling is filed at `feature-backlog/60-io-dispatch-silence`.

**None of this stitch's substance changed.** The bridge is still localhost
only — 8880 in, and one OSC client hardcoded to `127.0.0.1:6662`, which is the
*engine*, not `bopos.py`. Every question here is untouched: which transport
carries the address list device → dashboard, whether probing contends with a
live peripheral, "no bus" vs "bus present, nothing on it", the bus number, and
the contract amendment. The relay this builds is still what `2`, `3` and `4`
ride on.

Line references have drifted slightly with the io rework — `/io/scan` is now
`python/io/main.py:187`, the `/os/probe` reply `python/bopos.py:1567`,
simfleet's `has_i2c` `tools/simfleet.py:480`.
