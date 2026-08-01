# node-contract-fixes

**Free-floating — small code deltas that make the Node Contract true. Good first
codex-implement candidates.** Contract: `docs/OSC-CONTRACT.md` §1–§2, §11.

1. `python/io/sys_i2c.py`: `SMBus(bus)` opens outside the per-address try — no
   `/dev/i2c-1` throws uncaught. Degrade like `sys_wireless.read_wireless` does:
   no bus → empty scan, no crash; `/io/create` on a busless node replies
   `/io/error <name> no-bus`.
2. `bash/start.sh:12`: read the MAC from the discovered primary interface, not
   hardcoded `wlan0` (wired x86 boxes have no wlan0). Same for the `/home/pi`
   hardcoded paths where cheap.
3. Targeted process management: replace `bash/stop.sh`'s `pkill python` (kills
   helper/io/anything) and helper.py's `pkill pd; pkill jackd` with targeted
   stops (pidfiles or pkill -f on exact entrypoints) — the ratified fix for
   `/patch`-restart fragility. `/os/restart-engine` (contract §7) lands here.

Each is independently shippable and testable on the laptop rig / simfleet. The
governing rule to verify against: *a node never crashes or falls silent for lacking
hardware.*
