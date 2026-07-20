# live parameter catch-up completion notes

The OSC bridge now tracks an appearance as pending until the assigned node
advertises its configured Seat ID. At that convergence heartbeat it invokes
the same per-Seat replay helper used by the manual `Send all` action. A
per-device appearance/rate record prevents steady heartbeats from replaying.

The helper derives its identity allowlist from `live_control_declarations()`,
so stale durable keys outside the staged promoted manifest remain unsent.
Physical and managed Simulation/audition identities traverse the same gate;
the manual replay action remains unchanged for operator use.

## Verification

Passed 2026-07-20:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py dashboard/osc_bridge.py \
  .loom/threads/live-param-catchup.stitching/verify_live_param_catchup.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/live-param-catchup.stitching/verify_live_param_catchup.py
git diff --check
```

The focused bridge-to-real-simfleet regression passed six checks: assignment
preceded parameter replay, the simulated node applied the value, steady
heartbeats sent no repeats, reconnection caused one fresh replay, managed
Simulation followed the same gate, and staged declarations excluded a stale
Seat parameter. OSC float assertions use float32 tolerance.

No hardware or installation-LAN test was performed. Bob's untracked
`dashboard/shows/` working material was untouched.
