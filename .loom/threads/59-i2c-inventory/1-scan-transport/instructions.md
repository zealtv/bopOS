# 1-scan-transport

**Status:** waits on `0a-io-design-review` · ends in a contract proposal for Bob
**Goal:** get a device's I2C address list to the dashboard, and build the path
from the io bridge to the dashboard that `2`–`6` ride on.

`0a` picks the transport; this stitch builds it. Rewrite this file from `0a`'s
ruling before claiming.

## Settle while building

- **"No bus" ≠ "empty bus".** `has_i2c` already says the first; an empty list
  must not mean both.
- **Bus number:** fixed at 1, or a parameter? Say why.
- **Contention:** if the scan can run outside the bridge, measure on the rig
  whether probing a live MPR121 or ADS1x15 disturbs it.

## Deliver

- Implementation in `python/bopos.py` and/or `python/io/main.py`.
- Additive amendment in `docs/OSC-CONTRACT.md` with a §15 entry — proposed to
  Bob first, since it's the wire.
- simfleet: a configurable fake address list (replacing `"has_i2c": False`) so
  `2` can test without hardware.
- A durable test in `tests/`.
