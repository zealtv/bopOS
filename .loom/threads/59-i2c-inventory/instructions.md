# 59-i2c-inventory

**Goal:** work with I2C sensors from the dashboard, no SSH: see what's on a
device's bus, bring a peripheral up and know it worked, watch its values live,
and patch against a real sensor on a real device while editing.

**Status:** `0`, `7` and `0a` tied. `0a` ratified 2026-10-04: `0a-io-design-review.tied/proposal.md`
is the design. Order: `1` → `2`, `3` → `77-performance-mode` → `8` → `9` → `6`.
`4` and `5` were dropped (folded into `9` and `6`).

## Origin

- Bob, 2026-08-05: *"it would be useful if in the device tab you could see the
  connected i2c devices."* The same day he brought up an ADS1115 on Ciro Toast
  by hand (SSH, `i2cdetect`, hand-written `ads.py` / `watch.py` —
  `session-2026-08-05-ciro-toast.md`). That widened the thread to **scan →
  identify → instantiate (and know it worked) → test**.
- Bob, 2026-10-03: *"I'm going to need to see in real time streaming I2C
  values. Our current debugging setup doesn't work particularly well for that.
  … When I go into patch edit mode, if I've got some devices in the fleet, I'd
  like to be able to pick a device and have its I2C values get streamed over to
  the patch that I'm editing … so I can work with a live sensor on a real
  device as I edit the patch."* → `6`, and the end of the "no streaming" rule
  for this layer.

## What exists

- **Bus scan:** `python/io/sys_i2c.py` (i2cdetect's strategy; `EBUSY` =
  present but kernel-owned, like the DAC). Takes a `skip` set for live
  peripherals.
- **Io bridge** (`python/io/main.py`) is **localhost-only**: listens on 8880,
  sends peripheral bundles at poll rate only to the engine on `127.0.0.1:6662`.
  The dashboard can't reach it.
- **`bopos.py`** reports only a boolean `has_i2c`, shown on the Device tab.
- **`tools/iosim.py`** fakes the bridge by sending to the engine's 6662 — the
  same door a live device stream would come through.

The missing piece is a path from the bridge to the dashboard and the editor.

## Binding constraints

- **An address is not a chip.** Hints OK, claims not.
- **Anything that touches a live peripheral goes through `io/main.py`**, which
  owns the registry. Two processes on one chip is a contention bug.
- **Streaming is now allowed here — deliberately, not by drift.** Contract §6
  removed streamed telemetry; Bob's 2026-10-03 ask reopens it for sensor
  development. `0a` decides its bounds and the §6 amendment.

## Stitches

- ~~`0-bridge-logging`~~, ~~`7-poll-timing`~~ — tied.
- `0a-io-design-review` — **ready.** One design for transport, streaming,
  ownership, workflow, simulation. Also answers split elements' i2c question
  (`62`).
- `1-scan-transport` — device→dashboard path + contract amendment. Needs `0a`.
- `2-device-tab-inventory` — show the addresses. Needs `1`.
- `3-peripheral-lifecycle` — create/destroy/re-init from the dashboard, and see
  failures. Needs `1`. Carries two standalone defects.
- `4-sensor-test-window` — "test this sensor for N seconds". Needs `3`; `0a`
  may fold it into live streaming.
- `5-simulated-input` — fake sensors for patching without hardware. Needs `0a`.
- `6-live-sensor-in-patch-edit` — stream a fleet device's sensor values into
  the patch being edited. Needs `0a`.

Expect `0a` to merge, split or retire `1`–`6`.

## Supporting files

`session-2026-08-05-ciro-toast.md` (transcript), `ads.py`, `watch.py` (the
scripts that answered the questions).
