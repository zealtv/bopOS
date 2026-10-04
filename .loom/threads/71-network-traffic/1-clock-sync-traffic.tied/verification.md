# 71/1 verification — approved stage A build (71/1a)

## Stage A implementation

`dashboard/osc_bridge.py` now carries the observed pong source into sync
handling and sends each physical offset to the known responding device's IP
on the configured node command port (6660 by default), using the existing LAN
source selection. No missing/invalid route falls back to broadcast. Endpoint
identity includes device/Seat object generation, IP, concrete ID, execution
mode/relay destination, and editor generation. Old samples and device sync
facts are cleared on route changes; echoed leader timestamps before a boundary
are rejected. Heartbeat IP changes/reappearance, assignment/unassignment,
object replacement, Seat reindex, removal/offline and a newer probe revealing
a backwards node monotonic clock invalidate the generation. Periodic cleanup
uses the existing ping tick, without adding a timer or changing its cadence.

Physical pongs cannot drive Simulation/Patch Edit. Virtual corrections remain
on the shared loopback execution relay; Patch Edit's active editor uses its
existing concrete ID 0. Relay/mode transitions reject old in-flight echoes.
No node code, estimator formula/window/constants, slew duration, cadence,
OSC address/payload or `.pd` file changed. Stage B remains deferred.

**Contract:** §3.1 already specifies unicast offsets and concrete selectors;
no contract edit or clarifying normative prose is needed for this correction.

## Focused regression and stage A measurement

```sh
~/.venvs/bopos/bin/python tests/test_sync_protocol.py
~/.venvs/bopos/bin/python .loom/threads/71-network-traffic/1-clock-sync-traffic.stitching/measure_traffic.py
~/.venvs/bopos/bin/python .loom/threads/71-network-traffic/1-clock-sync-traffic.stitching/verify_traffic.py --results-dir .loom/threads/71-network-traffic/1-clock-sync-traffic.stitching/stage-a
```

Focused suite: **20 tests passed**, including routing/source validation, missing
or unsafe peers, duplicate IPs, two virtual nodes sharing a relay, DHCP and
heartbeat reappearance, fast same-IP reboot, object/Seat replacement, reindex,
offline/removal, assignment boundaries, late/reordered replies, failed sends
without fallback, and Live/Simulation/Patch Edit isolation. The existing
estimator and node scheduler/slew checks still pass.

The measurement script now supplies current stable endpoint fixtures and the
observed source IP to production pong handling. It records destination/route
per sync message type and counts intended broadcast sends. Default output is
`stage-a/`, preserving original proposal JSON/logs. The transport interception
still delivers only to localhost; real broadcast/unicast packet capture is a
hardware check, not a claim from this run.

| Nodes | Pings / pongs / offsets in ~12 s | Broadcast sync packets/s | Broadcast offsets | Complete events | Callback spread median / p95 / max (ms) |
|---:|---:|---:|---:|---:|---:|
| 4 | 24 / 96 / 96 | 2.000 | 0 | 20 / 20 | 0.111 / 0.137 / 0.155 |
| 16 | 25 / 400 / 400 | 2.083 | 0 | 20 / 20 | 0.138 / 0.201 / 0.269 |
| 32 | 23 / 736 / 736 | 1.916 | 0 | 20 / 20 | 0.237 / 0.415 / 0.475 |
| 50 | 24 / 1,200 / 1,200 | 2.000 | 0 | 20 / 20 | 0.371 / 0.719 / 0.779 |

Every measured offset used `127.0.0.1:<node-command-port>` / physical route,
the simulator's known endpoint. Only `/sync/ping` selected the installation
broadcast destination. At 50 nodes total traffic remains ~202 sync packets/s;
stage A changes routing, not the number of corrections. The model goes from
102 broadcast sync packets/s to 2 at 50 nodes. Evidence checks pass against
raw logs, per-kind routes/counters and all 80 complete events. The original
baseline evidence checker also still passes.

## Required software tiers

`./tools/run-tests.sh fast`: **535 tests passed** on the final code/test set.
The initial pass had 533 before adding two heartbeat/shared-relay regressions.
`./tools/run-tests.sh browser`: **all 32 journeys passed**, including execution
mode routing, IO control/streams, Monitor, event control and snapshot replay.
Touched Python files compiled, and `git diff --check` passed.

No real Pi, installation LAN/AP, Pd or audible timing gate ran. Bob's hardware
list: packet capture must confirm ~2 sync broadcasts/s, unicast corrections to
current node IPs after DHCP/reboot and no virtual corrections on the LAN;
common-clock audio recording remains required by `sync-4-hw-measurement`.
These simulator callback spreads do not discharge that hardware gate.
No commit, loom commands or sibling-worktree operation.

## Original design-gate evidence (historical record)

The following sections describe the earlier proposal-only baseline, before
Bob approved stage A. Their original data remains beside the proposal;
the stage A observations above are retained separately.

## Scope and environment

Main checkout, Darwin 23.6.0 arm64, project venv Python 3.14.7. Only this
stitch's measurement/design artifacts were created; the handoff report is in
Claude's scratchpad. No runtime/contract edits, commit, loom command, physical
rig or sibling worktree operation. The pre-existing tracked deletion of the
unclaimed stitch instructions reflects its move into this `.stitching` directory.

## Executed measurement

From the repository root:

```sh
~/.venvs/bopos/bin/python .loom/threads/71-network-traffic/1-clock-sync-traffic.stitching/measure_traffic.py
```

UDP binding required the approved outside-sandbox execution. All datagrams
were sent to `127.0.0.1`; the production bridge's requested execution target
was intercepted in this measurement process, never transmitted to the LAN.
The benchmark imports the production loop/estimator, without starting the
dashboard service or changing files outside the stitch. Other traffic is
ignored by the measurement receiver and excluded from sync counters.

Four fleets: 4, 16, 32 and 50 nodes. Ten-second warm-up, twelve-second counting
window, twenty scheduled events per fleet, 500 ms lead. Production randomized
ping cadence; leader RNG seed 7100+N. Simulator fixed skews are randomly chosen
and retained in raw logs; no drift or timestamp noise was injected. Exact
latencies and byte totals are observations, not deterministic test expectations.

All 80 events fired on every node in their respective fleet; all 102 simulated
nodes acquired offset targets. At 50 nodes: 24 pings, 1,200 pongs and 1,200
offsets during the counting window; 201.97 packets/s and 10,830.12 OSC B/s.
Event callback spread median/p95/max: 0.388/0.836/1.167 ms. These single-host,
single-simulator-process results do not verify independent node slewing,
Wi-Fi, Pd, acoustic/audio timing or slow-poll holdover.

Artifacts: `traffic-results.json`, `simfleet-{4,16,32,50}.log` and
`measure_traffic.py`. JSON retains counters, rates by message kind, intended
routes, final target errors, RTT and callback spreads. Proposed traffic models
were regenerated after the run using explicit OSC query encoding; measured
observations were preserved. Post-run script changes added completeness guards
and explicit query encoding, without changing the executed production loop.

## Retained-evidence check — PASS

```sh
~/.venvs/bopos/bin/python .loom/threads/71-network-traffic/1-clock-sync-traffic.stitching/verify_traffic.py
```

Checks independently encoded representative datagram lengths, current/proposed
model agreement, exact fleet coverage of every event from raw logs, recomputed
spread summaries, acquired-target/error counts, counter ratios, rate arithmetic
and intended routes. Result: four complete fleets and 80 complete events.

Two corrected measurement-development issues: the old harness's unsupported
`--meter-interval` argument was removed from this new script before successful
measurement; explicit query serialization revealed an additional four bytes
of OSC type-tag padding. The final proposed models include it. The old harness
and simulator runtime were not edited.

Python syntax and `git diff --check` passed. Runtime suites were not run for
this artifact-only design gate. Hardware qualification is pending Bob's rig;
see the `sync-4-hw-measurement` plan in `proposal.md`. No real-fleet or adaptive
timing pass is claimed.
