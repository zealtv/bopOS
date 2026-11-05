# 71/2 verification — proposal half

## Scope

Measurement scripts, results and proposal live in this stitch; the handoff
report lives in Claude's scratchpad. No runtime/contract edits by this task,
no commit, no loom commands, and no sibling-worktree operations. Concurrent
59/8 main-checkout integration was read only where relevant to the shared IO
consumer seam. Source SHA-256 values in `monitor-results.json` were unchanged
during the successful measurement.

## Localhost transport run — completed

```sh
~/.venvs/bopos/bin/python .loom/threads/71-network-traffic/2-monitor-transport.stitching/measure_monitor.py
```

Darwin 23.6.0 arm64; project venv Python 3.14.7. Approved outside-sandbox
execution was needed to bind local UDP/HTTP/WebSocket ports. The preceding
sandbox attempt failed at the first socket bind; it made no measurement.

The script constructs the production Dashboard with temporary data, empty
asset/patch roots and fifty bound Seats under the stitch. It starts real OSC
loops against simfleet at `127.0.0.1`, serving the production WebSocket handler
through a minimal loopback FastAPI endpoint. The source's 5551 listener gets
an ephemeral measurement port; no actual IO stream consumer is opened. Instance
hooks count queued/publication events while executing the original methods.
The actual WebSocket transports are drained independently; compression is off.
No browser, Pd, physical hardware, Wi-Fi or stalled-writer test ran.

Acquisition warm-up 12 s; 3 s settling before each 12 s counting phase. Source
heartbeat interval 10 s; one moving orbit in the moving phases. Four phases:
no clients/static, one client/static, one client/moving, three clients/moving.
Exact counts vary with jitter, random RSSI changes and counting-window edges.

Results: ~312 WS messages/s for a static one-client fleet, ~362/s moving;
~1,048/s total with three moving-point clients. No-client phase still queued
3,772 broadcast tasks (~314/s). The measured point loop ran ~24.08 Hz. Each
peer's uncompressed JSON byte/message counts are retained; the first peer's
12,275 received JSON messages are in `ws-observations.jsonl`. The proposal
contains the rate tables and per-kind breakdown. `simfleet-50.log` is retained.
Temporary fixture directories were removed on normal exit; sockets/processes
were closed. A later script-only adjustment suppresses child bytecode writing
for future runs; it does not change production traffic.

## Unhandled-event replay — PASS

```sh
node .loom/threads/71-network-traffic/2-monitor-transport.stitching/check_pending.cjs
```

Uses shipped `ws.js` in a VM with a fake WebSocket, replaying retained messages
through its actual `emit()` method. Main app case registers inert handlers for
measured consumed types; repository JS is checked for any actual `sync`
handler before asserting its absence. Remote case extracts actual literal
handler registrations from `facilitator.js`.

Retained pending objects: main `sync` 3,453; Remote 12,077 total (3,699
`osc_in`, 4,101 `osc_out`, 246 `heartbeat`, 3,453 `sync`, 578 `point_frame`).
This confirms the queue path, not browser heap bytes or CPU. Results are in
`pending-results.json`.

## Retained-evidence check — PASS

```sh
~/.venvs/bopos/bin/python .loom/threads/71-network-traffic/2-monitor-transport.stitching/verify_measurement.py
```

Recounts first-peer message types and uncompressed Starlette-style JSON byte
sizes from raw observations; verifies phase/node counts, queue/publication
agreement, tap-class totals, peer count, bounded window-edge skew, moving-point
dual publication and pending-replay consistency. Result: four phases, 50
nodes, 12,275 retained messages; all checks pass.

Python AST parsing, Node syntax check and stitch-local trailing-whitespace
checks passed. `git diff --check` passed. Runtime/browser suites were not run
for this proposal-only task. No subscribed/batched runtime has been implemented
or benchmarked: its numerical caps and projected frame reduction are proposed.
Slow-client isolation, browser heap/CPU, real devices, Modules panels and
original-rate audio/editor fidelity need the implementation/physical gates
listed in `proposal.md` after Bob's ruling.
