# feature-backlog

**Goal:** park features Bob wants later, out of the active queue.

Parking changes priority only — it doesn't drop, narrow or ratify anything.
Each feature keeps its own thread; its loose leaf is `.waiting`. To revive, Bob
says so, then `loom.sh resume` it (or move it back to the top level).

`34-fleet-patch-global-state` and `48-morph-interpolation` were dropped on
2026-10-03 (folded into `66-projects`; presets removed by `65`). `60-io-dispatch-silence` was absorbed
into `67-repair-pass/3-io-bridge-hardening` the same day, and
`33b-device-network-config` was revived to the top level.

| feature | what | parked |
|---|---|---|
| `49-remote-ipad-restyle` | touch-first restyle of Remote, on a real iPad | 2026-07-30 |
