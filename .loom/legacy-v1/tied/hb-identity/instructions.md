# hb-identity

**Do first (with `assign-persistence`) — this is Crux 1's load-bearing half.**
Contract: `docs/OSC-CONTRACT.md` §5–§6. Reasoning: `schema-design-draft` (tied) —
`judgment.md` §3C, `ratification.md`.

Move the heartbeat out of PD into helper.py and give it identity:

- `/os/hb <uid> <id> <version> <engine-alive 0|1> [rssi]` (shorthand `/hb`), sent by
  helper.py **directly to 5550** every 10 s — 2 s while unassigned (id −1). The fast
  heartbeat is discovery; there is no hello family.
- `uid` = persisted machine token → primary-interface MAC (discovered, **not**
  `wlan0`-hardcoded) → per-boot UUID. Strings, not floats.
- `engine-alive`: helper checks the engine process is up (engine death ≠ device death).
- `rssi` optional-by-absence, switchable via `bopos.config`; reuse
  `io/sys_wireless.read_wireless` degradation.
- `/all/os/ping <token>` → unicast `/os/pong <token> <uid>` (retires `/echo`).
- `/os/identify` — chirp/flash to locate the box (this is what `/aloha` has been used
  for; route the chirp through the engine or a system beep — coordinate with Bob for
  any PD-side hook, **never edit .pd yourself**).
- `/all/os/mute <0|1>` — **safety-critical**: transport-level silence below patch
  logic (amixer on Pi; degrade to engine-stop). Broadcast, idempotent, spam-safe —
  repeated sends always converge on silence.

Removing the old PD-side `/hb` and `/aloha` emitters is Bob's edit — flag it in the
stitch, don't touch `.pd` files.

Verify in `simfleet` (dashboard-0-sim-fleet; per CLAUDE.md, protocol features land in
the simulator in the same stitch — build the minimal simfleet node behaviour here if
that stitch hasn't run yet). Hardware verification needs Bob or a live rig — say so
rather than claiming it.
