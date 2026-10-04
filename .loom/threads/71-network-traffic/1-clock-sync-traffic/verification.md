# 71/1 verification — design gate

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
