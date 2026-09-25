# 1-scan-transport

**Status:** blocked on `0a-io-design-review` · ends in a contract proposal for Bob
**Goal:** get the connected I2C address list from a device to the dashboard,
and build the relay `2`–`4` ride on.

`0a` decides the transport; this stitch implements it. The options below are
input to `0a`.

## Options

1. **`bopos.py` scans** on `probe i2c` → `/os/probe <id> i2c <addr>…`. Cheap,
   but widens `/os/probe` from "report held values" to "go and look", and can't
   `skip` live peripherals.
2. **`bopos.py` relays to the bridge** on 8880; bridge replies to `bopos.py`.
   Correct `skip`; adds a localhost request/reply with timeout and needs the
   bridge up.
3. **`i2c` array in `/os/report`.** Cheapest UI, but scans on every report for a
   fact that rarely changes.

## Resolve before implementing

- **Contention:** does probing an address mid-transaction disturb it? Measure on
  the rig with a live MPR121 or ADS1x15. If yes, option 1 is out.
- **"No bus" ≠ "empty bus".** `has_i2c` already says the first; don't let an
  empty list mean both.
- **Bus number:** fixed at 1, or a parameter? Say why.

## Deliver

- Implementation in `python/bopos.py` (and `python/io/main.py` if relayed).
- Additive amendment in `docs/OSC-CONTRACT.md` with a §15 entry.
- simfleet parity: a configurable fake address list (replacing
  `"has_i2c": False`) so `2` can test headlessly.
- A durable test in `tests/`.

Write the proposal here, mark `.waiting`, surface to Bob — it's the wire.

Note: PD-side `scan` now reaches the bridge correctly (`bd2d989`); that doesn't
change anything above.
