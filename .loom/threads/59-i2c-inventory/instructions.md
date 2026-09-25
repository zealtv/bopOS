# 59-i2c-inventory

**Goal:** detect, instantiate and test an I2C sensor on a device from the
Device tab — no SSH.

**Status:** `0` and `7` tied. Everything else is gated on
**`0a-io-design-review`** (ready, first in queue, ends in a Bob-ratified
proposal).

## Origin

- Bob, 2026-08-05: *"it would be useful if in the device tab you could see the
  connected i2c devices."*
- Same day, Bob brought up an ADS1115 on Ciro Toast by hand (SSH, `i2cdetect`,
  hand-written `ads.py` / `watch.py` — see `session-2026-08-05-ciro-toast.md`).
  That widened the thread from "show addresses" to the whole workflow:
  **scan → identify → instantiate (and know it worked) → test**.

## What exists

- **Bus scan:** `python/io/sys_i2c.py` (i2cdetect's strategy; `EBUSY` = present
  but kernel-owned, like a DAC). Takes a `skip` set for live peripherals.
- **Io bridge** exposes `/io/scan`, but is **localhost-only**: listens on 8880,
  replies only to the engine on 6662 (`PD_PORT` in `python/io/main.py`). The
  dashboard can't reach it.
- **`bopos.py`** imports `sys_i2c` but only reports a boolean `has_i2c`, shown
  on the Device tab.

So the missing piece is a path from the bus (via the bridge) to the dashboard.

## Binding constraints

- **An address is not a chip.** Hints OK, claims not.
- **Anything that touches a live peripheral goes through `io/main.py`**, which
  owns the registry. Two processes on one chip is a contention bug.
- **No streaming.** Contract §6 deleted the meter plane and declined leased
  probes. Bounded windows returning one summary are fine.

## Stitches

- ~~`0-bridge-logging`~~ — tied. Bridge output now reaches a logfile.
- ~~`7-poll-timing`~~ — tied. ADS1115 sample rate / poll period fixed.
- `0a-io-design-review` — **ready, first in queue.** One design for transport,
  peripheral ownership, debugging workflow, simulation. Also carries split
  elements' i2c question (`62`).
- `1-scan-transport` — device→dashboard path + contract amendment. Needs `0a`.
- `2-device-tab-inventory` — show the addresses. Needs `1`.
- `3-peripheral-lifecycle` — create/destroy/re-init from the dashboard, and see
  failures. Needs `1`. Contains two standalone defects (silent create failure;
  LIS3DH dead after reconnect).
- `4-sensor-test-window` — "test this sensor for N seconds" → verdict + exact PD
  values. Needs `3`.
- `5-simulated-input` — simulated sensors for patching without hardware. Needs
  `0a`. Wanted, not urgent.

`0a` may merge, split or retire `1`–`5`; expect it to revise this list.

## Supporting files

`session-2026-08-05-ciro-toast.md` (transcript), `ads.py`, `watch.py` (the
scripts that answered the questions).
