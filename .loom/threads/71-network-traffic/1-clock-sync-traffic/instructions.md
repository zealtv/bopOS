# 1-clock-sync-traffic

**Status:** ready · **design gate** — proposal for Bob (it's the wire,
contract §3.1)
**Goal:** a clock-sync design that keeps events within budget (< 10 ms typical)
while sending far less traffic, especially broadcast.

Bob, 2026-10-03: *"assess the clock-sync messages and see if there is a better
design to keep sync but reduce traffic."*

## Today (`dashboard/osc_bridge.py`, `python/sync_node.py`)

- Dashboard broadcasts `/sync/ping <seq> <leaderTime>` at ~2 Hz, jittered.
- Every assigned node unicasts `/sync/pong` back.
- **For every pong** the dashboard sends `/<id>/sync/offset <ns>` to the
  execution target — by default `255.255.255.255`. So each node's correction is
  broadcast to the whole fleet, ~2 Hz per node, forever. At 52 nodes: ~100
  broadcast datagrams/s that 51 of 52 nodes discard. Wi-Fi broadcast goes at
  the basic rate, without retries, and costs everyone airtime.
- The ping never stops or slows once offsets have settled.

## Assess

1. **Measure first** — on simfleet at 50 nodes and, if possible, the rig:
   datagrams/s and bytes/s by type, and current sync quality
   (`tools/sync_measure.py`).
2. **Options to weigh** (not a decision):
   - Unicast offsets to the node's IP instead of broadcasting.
   - Let nodes compute their own offset: the leader's broadcast ping carries
     its time; a node estimates offset from ping arrival times plus an
     occasional unicast RTT probe — no per-node offset message at all.
   - Adaptive rate: fast while converging or after a jump, slow (e.g. 0.1 Hz)
     once stable; a node falling silent triggers fast mode again.
   - Bundling: one broadcast carrying all offsets, if per-node messages stay.
   - Standard tools (chrony/PTP) on the nodes vs keeping it in bopOS.
3. Rules that still bind (`fleet-testing/clock-sync`): nodes use
   `time.monotonic()`, slew never step, Pd never sees absolute time.

## Deliver

`proposal.md`: measurements, recommended design with rejected alternatives,
expected traffic at 10/50/100 nodes, contract amendment text (proposed), and
how `sync-4-hw-measurement` would verify it. Mark `.waiting`, surface to Bob.
