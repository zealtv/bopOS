# feature-backlog

**Goal:** park features Bob wants later, out of the active queue.

Parking changes priority only — it doesn't drop, narrow or ratify anything.
Each feature keeps its own thread; its loose leaf is `.waiting`. To revive, Bob
says so, then `loom.sh resume` it (or move it back to the top level).

| feature | what | parked |
|---|---|---|
| `33b-device-network-config` | saved Wi-Fi profiles + write-only passphrases from the Device tab | 2026-07-23 |
| `34-fleet-patch-global-state` | "the fleet patch" as global state, shown in the menu bar | 2026-07-23 |
| `48-morph-interpolation` | `morph` grammar: glide generator arguments between presets | 2026-07-29 |
| `49-remote-ipad-restyle` | touch-first restyle of Remote, on a real iPad | 2026-07-30 |
| `60-io-dispatch-silence` | test + last silent path in io bridge dispatch | 2026-08-05 |
