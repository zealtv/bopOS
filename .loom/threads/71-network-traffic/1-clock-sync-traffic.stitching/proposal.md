# Clock sync with less network traffic — proposal for Bob

**Status, 2026-10-05:** Bob approved stage A; its implementation and software
verification are recorded in `verification.md` (71/1a). Stage B is deferred.
The design and baseline measurements below are the original proposal record;
stage A rerun evidence is retained separately in `stage-a/`. §3.1 needed no
contract change because it already requires unicast offsets.

**Recommendation:** first unicast each offset to its node, keeping today's 2 Hz
clock estimator. At 50 nodes this removes 100 of the 102 broadcast sync packets
per second, with no new wire address. Then qualify an optional per-node unicast
probe with adaptive polling: fast during acquisition, up to ten seconds between
probes only when measured drift and uncertainty permit it. A fully stable
50-node fleet would use about 15 sync packets/s instead of 202, with no sync
broadcasts. That second step needs Bob's wire ruling and real-fleet evidence.

This is a design gate. No runtime or contract changes have been made. The
localhost measurements below establish traffic and a software baseline; they
do not establish <10 ms timing on installation Wi-Fi or at the audio outputs.

## What the code does today

`dashboard/osc_bridge.py:251` sends one `/sync/ping` every 500±100 ms. Each
reachable node answers `/sync/pong` to the leader, including unassigned nodes
(`python/bopos.py:1556`). The leader accepts only assigned devices' samples,
rejects RTT outside 0–200 ms, and takes a median of offsets whose RTT is within
1.5× the minimum of its last 16 samples. After three samples it sends one
absolute offset for every accepted pong (`osc_bridge.py:1914–1955`).

That offset uses `send()`, whose execution destination defaults to
`255.255.255.255:6660`. **The existing §3.1 table already specifies unicast
offsets.** The implementation diverges from that table. `send_for_uid()` is
also insufficient: its physical path still uses the installation destination,
not a device IP. Simulation and Patch Edit change the execution destination;
the correction must reach the endpoint whose pong produced the estimate.

Nodes use integer monotonic nanoseconds and slew their working offset over
about one second (`python/sync_node.py`). Events convert leader time to local
time by adding that offset; Pd receives the event only when due. Sync is also
needed for LFO/automation phase, so an idle show cannot simply stop polling.
Today's `synced()` means a target was received once, without a freshness lease.

### Traffic calculated from the encoder

Assume N responsive, assigned nodes, steady state, mean 2 Hz, and no losses.
Each second: **2 pings + 2N pongs + 2N offsets = 2+4N datagrams**. Broadcast
traffic is **2+2N datagrams**. With A assigned and U unassigned responders,
total becomes 2+4A+2U; unassigned nodes still generate pongs.

Sizes below use actual OSC encoding: 15-digit monotonic timestamps, a
17-character UID, an eight-digit negative offset, and concrete IDs 1…N.
Ping = 36 B, pong = 76 B, offset = 32 B for IDs 1–99, 36 B for ID 100.
Decimal lengths and OSC's four-byte padding change these sizes in practice.
“IPv4+UDP” adds 28 B/datagram; neither column includes link headers, AP
forwarding, retries, encryption, or audio/heartbeat/other control traffic.

| Nodes | Total packets/s | OSC B/s | IPv4+UDP B/s | Broadcast packets/s | Broadcast OSC B/s |
|---:|---:|---:|---:|---:|---:|
| 4 | 18 | 936 | 1,440 | 10 | 328 |
| 10 | 42 | 2,232 | 3,408 | 22 | 712 |
| 16 | 66 | 3,528 | 5,376 | 34 | 1,096 |
| 32 | 130 | 6,984 | 10,624 | 66 | 2,120 |
| 50 | 202 | 10,872 | 16,528 | 102 | 3,272 |
| 100 | 402 | 21,680 | 32,936 | 202 | 6,480 |

For an ordinary node, its own pong and offset contribute 4 packets/s and
216 OSC B/s to fleet traffic, plus its share of the common ping. It sends
152 OSC B/s and needs 136 incoming OSC B/s (ping plus its own offset). With
today's broadcast offsets it instead receives all nodes' corrections: at
50 nodes, 3,272 incoming OSC B/s, of which 3,136 are other nodes' offsets.
These receiver deliveries are not additional leader-originated datagrams.

Wi-Fi airtime savings cannot be computed from these byte totals alone. AP
configuration and power saving matter; Cisco documents buffering broadcast
and multicast until DTIM delivery. Measure the installation AP rather than
assuming a particular broadcast rate or forwarding policy.
([Cisco WLAN settings](https://www.cisco.com/c/en/us/td/docs/wireless/controller/8-5/config-guide/b_cg85/per_wlan_wireless_settings.html))

## Localhost measurement

`measure_traffic.py` exercises the **actual production ping loop and pong
estimator**, with their default jitter, against `tools/simfleet.py`. Its
instance-local transport hook records the intended broadcast destination but
sends only to loopback. Each fleet gets ten seconds of warm-up, twelve seconds
of sync counting, then twenty events with 500 ms lead while sync continues.
Pings/offsets are counted at send; pongs at leader receive. JSON and raw logs
are retained beside this proposal.

| Nodes | Ping / pong / offset counts (12 s) | Total packets/s | OSC B/s |
|---:|---:|---:|---:|
| 4 | 24 / 96 / 96 | 18.00 | 935.90 |
| 16 | 25 / 400 / 400 | 68.75 | 3,666.58 |
| 32 | 23 / 736 / 736 | 124.56 | 6,661.18 |
| 50 | 24 / 1,200 / 1,200 | 201.97 | 10,830.12 |

Every node received a target, and all twenty events fired on every node in
each run. Timing statistics are in milliseconds:

| Nodes | RTT median / p95 | Final target error maximum | Event spread median / p95 / max |
|---:|---:|---:|---:|
| 4 | 0.383 / 0.572 | 0.027 | 0.117 / 0.136 / 0.330 |
| 16 | 0.519 / 0.814 | 0.042 | 0.150 / 0.276 / 0.330 |
| 32 | 0.806 / 1.421 | 0.047 | 0.221 / 0.342 / 0.495 |
| 50 | 1.128 / 1.998 | 0.035 | 0.388 / 0.836 / 1.167 |

All measured ping and offset sends selected the execution broadcast target;
the hook prevented LAN transmission. Finite windows vary around 2 Hz because
production pings are jittered. Actual offsets can encode shorter than the
representative model.

The simulator uses one process and one host clock, with fixed artificial
offsets (±40 ms) and zero timestamp noise. It replies sequentially and applies
offsets directly: it does **not** exercise real node slewing, oscillator drift,
independent OS scheduling, Wi-Fi asymmetry/loss, Pd, or audio hardware.
Event spread is max−min logged simulator callback time, not recorded sound.
RTT includes both processes' scheduling and reply work. Reported estimate
errors compare final targets with the simulator's known fixed offsets.

The older `tools/sync_measure.py` cannot provide this production baseline as
written: it uses 10 Hz probes and passes the retired `--meter-interval` option
to simfleet. This stitch reuses only its fire-log parser/spread calculation;
the new measurement script uses today's supported simulator arguments. The
old harness has been left unchanged.

## Recommended implementation, in two stages

### A. Restore unicast offsets, retain the current estimator and cadence

Carry the observed source IP into pong handling and associate it with the
known UID, current seat and endpoint generation. Send corrections to that
physical IP on 6660, using the existing LAN source-selection machinery.
Invalidate the association on reboot, replacement, IP/seat change or removal;
do not broadcast a correction when no current endpoint is known. A new
accepted pong restores the route. Constrain physical/virtual routing to the
active execution mode, and preserve the shared loopback relay for virtual
nodes without leaking its corrections onto the LAN. A UID identifies the
node; the concrete seat ID remains the offset address selector.

This changes neither time encoding, estimator nor node behavior. Total sync
traffic stays as in the first table. Broadcast falls to **2 packets/s and
72 OSC B/s**, independent of fleet size: a 98% packet reduction at 50 nodes.
This is the first useful delivery even if adaptive polling fails qualification.

### B. Directed probes and adaptive polling, after qualification

Add `/sync/query <seq> <leaderTimeNs> <uid>` sent unicast to one node on 6660.
Only that UID responds, using the existing `/sync/pong` reply. Explicit UID
matching also makes shared-IP virtual relays safe. Keep `/sync/ping` as the
legacy fleet-wide broadcast; do not silently change its grammar or transport.

Use existing discovery/heartbeats to find assigned endpoints. Stagger each
node's probes independently rather than asking the whole fleet at once.
Start at 2 Hz per node; require at least three usable measurements **and
demonstrated settling of the working clock**, not merely receipt of a target.
Advance through 1 s, 2 s, 5 s and at most 10 s intervals only while fresh
low-RTT samples, offset residuals and measured frequency uncertainty meet the
error budget. Slow polling starts as an opt-in fleet profile, not a changed
default. A mixed or unqualified fleet stays on stage A's 2 Hz broadcast ping.

Maintain at most one outstanding query per UID, with a 200 ms reply deadline.
Accept only its exact UID/seq/echoed timestamp from the current endpoint;
ignore duplicates and late replies. A missing/bad reply or changed clock
residual returns **that node** to acquisition. Fast retries are bounded to
five seconds, then back off 1/2/4/10 s while rediscovery continues. One silent
node must not accelerate every other node. On leader/node restart or route
generation change, discard that node's estimator and pending query.

Do not simply enlarge today's 16-sample window in time: at 0.1 Hz it spans
roughly 160 seconds instead of eight. Store each sample's monotonic epoch;
fit offset versus leader time using fresh, low-RTT samples and project the
estimate to the current leader epoch. Bound fit residuals, sample age and
frequency uncertainty; if they cannot support holdover, retain fast polling.
The wire still carries only the current **absolute offset**. Nodes retain
their monotonic slew and deadline conversion; there is no frequency wire
token and no stepping the working clock.

Expose freshness/holdover in backend diagnostics (UI wording is a separate
ruling). During silence keep the working clock and current event late-fire
policy; do not falsely claim the <10 ms budget after its uncertainty lease
expires. Do not reset the offset or LFO phase merely because a reply is late.

#### Timing budget that must be demonstrated

Proposed engineering allowance for cross-node spread: ≤3 ms estimation and
slew residual, ≤2 ms additional drift during holdover, and ≤4 ms scheduling,
Pd and audio-output variation, leaving 1 ms margin to the 10 ms target.
These are qualification limits, **not measured Pi/Wi-Fi results**. Define
“typical” for the gate as p95 event spread <10 ms; also publish median, p99,
maximum, drops and recovery time so the percentile cannot hide failure bursts.

If each node's residual frequency error is bounded by b ppm relative to the
leader, worst-case pair drift is 2b microseconds/second. A ten-second holdover
adds 0.2 ms at 10 ppm, 2 ms at 100 ppm, or 10 ms at 500 ppm. With a 1 ms
per-node drift allowance, choose T ≤ 1000/b seconds, capped at ten seconds;
include estimator/sample age and the one-second slew in the effective age.
The bounds must cover temperature, CPU load and system clock frequency
adjustment, not just a short quiet fit. If b is unknown or the uncertainty
exceeds budget, the node is ineligible for slow polling.

Three pongs do not establish that a newly booted node has converged: independent
monotonic epochs can differ by hours, and today's repeated pushes restart the
slew. Exercise that real startup path before claiming an acquisition time.
No large-target shortcut may step a clock while audio runs.

#### Expected quiet-fleet traffic (conditional, not measured)

One query/pong/offset exchange per node every ten seconds: 0.3 packets/s and
16.8 OSC B/s per node, or 25.2 IPv4+UDP B/s. The query is 60 B: the UID adds
20 B and its extra OSC type tag grows the padded type-tag field by 4 B.

| Nodes | Total packets/s | OSC B/s | IPv4+UDP B/s | Sync broadcasts/s |
|---:|---:|---:|---:|---:|
| 4 | 1.2 | 67.2 | 100.8 | 0 |
| 10 | 3 | 168 | 252 | 0 |
| 16 | 4.8 | 268.8 | 403.2 | 0 |
| 32 | 9.6 | 537.6 | 806.4 | 0 |
| 50 | 15 | 840 | 1,260 | 0 |
| 100 | 30 | 1,680.4 | 2,520.4 | 0 |

At 50 nodes, stage B's qualified quiet state reduces packets by 92.6% and
OSC bytes by 92.3%. At 0.5 Hz it would be 75 packets/s and 4,200 OSC B/s.
At 2 Hz acquisition it is **300 packets/s**, greater than today's 202:
directed probing buys isolation, not free startup traffic. Stagger startup
with a proposed fleet cap of 40 queries/s (≤120 exchange packets/s); at
50/100 nodes this necessarily stretches convergence beyond nominal 2 Hz.
Prioritize new/recovering nodes fairly and report the actual settling time.
Heartbeats and show traffic remain outside all these sync totals.

## Alternatives and why they are not the recommendation

| Option | Benefit | Cost / reason to defer |
|---|---|---|
| Shared ping slowed to 0.5 Hz, unicast offsets | At 50 nodes: 50.5 packets/s, 2,718 OSC B/s; no new address | Worth testing as the simplest intermediate profile, but one unstable node forces the fleet's shared cadence up; requires estimator aging and drift qualification too. |
| Shared ping at 0.1 Hz, unicast offsets | Only 10.1 packets/s at 50 nodes | More packet-efficient than directed queries, but all nodes still burst together and share recovery cadence. The same holdover limits apply. |
| Nodes compute offset from broadcast arrival, with occasional RTT | Removes leader offset pushes | One-way queue asymmetry becomes clock error. Current ping has no measured forward-delay bound; adds node estimator/drift logic and more wire coordination. Probe quality first rather than assume RTT/2 from an old exchange remains valid. |
| Bundle offsets in one broadcast | Reduces datagram count | Keeps O(N) offset bytes and all-node reception; correlated loss and MTU/chunking become new problems. A UID plus decimal offset per node reaches kilobytes at 100 nodes. No advantage over stage A for endpoint isolation. |
| Offset deadband only | Avoids redundant corrections | Leaves all 2N pongs/s and the shared ping. Can hide accumulating drift unless it has the same age/error safeguards; may be added later without changing absolute-state semantics. |
| Stop sync between show events | Lowest idle traffic | Breaks continuous phase and leaves the first event dependent on unqualified holdover. |
| chrony / PTP | Mature filtering and disciplined clocks | Larger deployment/clock-domain change. Chrony examples show accuracy depends on timestamping, delay symmetry and polling. NTP system-clock alignment does not by itself align independent monotonic epochs; bopOS would still need a safe mapping. PTP hardware-clock support is a hardware/driver capability, not a guarantee for the installed Pi/Wi-Fi path. Consider as a separate measured strategy, not a dependency of this fix. |

Primary references for the last option:
[chrony configuration and accuracy](https://chrony-project.org/examples.html),
[Linux PTP hardware-clock infrastructure](https://www.kernel.org/doc/html/latest/driver-api/ptp.html).

## Proposed §3.1 amendment — pending Bob's ratification

Stage A needs an implementation correction to the existing unicast table,
not a new wire token. If stage B is approved, add this row and replace the
fixed-cadence/grammar prose with the following proposed text:

| address | direction | transport | args |
|---|---|---|---|
| `/sync/query` | leader → one node | unicast, 6660 | `<seq:int32> <leaderTimeNs:string> <uid:string>` |

> The dashboard backend is the clock leader. The legacy fleet profile sends
> `/sync/ping` broadcast every approximately 500±100 ms. The directed profile
> sends `/sync/query` unicast to a known endpoint; only the node whose exact UID
> matches the third argument answers. Both probes receive `/sync/pong`, unicast
> to the probe source IP on 5550, echoing the sequence and leader timestamp and
> adding the responding UID and its monotonic timestamp at reply.
>
> Directed queries are tracked per UID; a reply is usable only for the current
> outstanding sequence/timestamp and endpoint generation. Polling is adaptive
> per node, fast during acquisition/recovery and slower only while the leader
> can bound clock uncertainty within the event budget. A silence or uncertain
> estimate does not authorize stepping the working clock.
>
> Offsets are sent to the responding node's current endpoint on 6660, using
> `/<id>/sync/offset` with a concrete assigned ID. Virtual endpoints use their
> execution relay; physical and virtual clock estimates must not cross routes.
> The offset remains the absolute device-minus-leader value at the current
> leader epoch, full-state and idempotent. Nodes slew it and schedule against
> their monotonic clocks; Pd never receives an absolute timestamp.
>
> `/sync/ping` remains selectorless, broadcast-only and fleet-wide.
> `/sync/query` is a second explicitly selectorless framework probe, scoped by
> its exact UID argument. `/sync/pong` retains its existing two-part reply
> grammar. All time-valued arguments remain decimal integer nanosecond strings;
> sequence numbers remain int32. Event and phase wire shapes are unchanged.

The exact polling constants, uncertainty fit and qualification profile are
implementation policy, documented and tested with the implementation. Deploy
stage B only to a fleet supporting the new query; until then keep legacy
probes with stage A unicast offsets. No extra capability token is proposed here.

## Code cost and verification before rollout

Stage A is small: dashboard source-aware pong dispatch, per-UID endpoint
routing/invalidation and execution-mode isolation; focused routing tests and
packet capture. Node code and timing estimator can stay unchanged. Verify
duplicate IP/shared relay, DHCP change, reboot/seat replacement, late pongs,
Simulation/Patch Edit and Live transitions. Never fall back to offset broadcast.

Stage B is medium: dashboard per-node scheduling, bounded pending probes,
fresh time-indexed estimator/frequency bounds, diagnostics; node exact-UID
query handling; simulator support and deterministic timing tests. Check drift
±10/100/500 ppm, changing drift, asymmetric delay, loss, duplication, reordered
and expired pongs, large epoch difference, leader restart, bounded retries and
fleet fairness. Exercise real `SyncState`/`EventScheduler`, not only simfleet's
direct-set clock. Verify long idle LFO phase as well as event bursts. Keep
stage A available as the rollout fallback.

### Hardware gate for Bob: `sync-4-hw-measurement`

1. Use at least three real Pis, their normal Pd/audio paths, and the actual
   installation AP; record Pi/image/audio-buffer versions, AP/channel/basic
   rates/DTIM/power saving, RSSI, fleet count and background load. Baseline
   today's implementation, then stage A, then the proposed adaptive profile
   using the same rig and event sequence. Capture at 10/50/100 real nodes if
   available; otherwise label the actual physical count and use simulator
   load only as additional load, never as physical-node evidence.
2. Capture OSC at the leader and an AP/radio observation point if available;
   distinguish host UDP counts from radio airtime, forwarding and retries.
   Stage A should leave ~2 sync broadcasts/s and no broadcast offsets. A fully
   qualified stage B fleet should match ~0.3N steady packets/s with no sync
   broadcasts. Save pcap plus per-node RTT/estimate/sample-age/interval logs.
3. Schedule ≥1,000 identical clicks with 500 ms lead after acquisition, through
   ≥30 minutes of quiet and realistic load, and after ten-second gaps. Record
   each device output on separate channels of a **single recorder/interface**
   with a common sample clock. Measure max−min onset per event from this shared
   recording; compare line outputs, or correct known acoustic path differences
   when measuring microphones. Cross-Pi monotonic log timestamps alone cannot
   measure real simultaneous sound.
4. Repeat cold boot, leader restart, one-node reboot, loss bursts, CPU/audio
   load, temperature changes and AP contention. Log initial epoch offsets,
   settling, drift bounds, lease expiry and recovery; test LFO phase through
   an idle period. A node's failure must not raise every node's probe rate.
5. Gate slow polling on p95 recorded event spread <10 ms, with p99/max/drops
   and time-to-settle reported alongside it, and no slew/phase discontinuity.
   Compare against baseline rather than declaring a passing median sufficient.
   If timing or holdover fails, retain stage A at 2 Hz and tune/measure before
   widening the adaptive profile. The existing hardware stitch remains
   unsatisfied until these physical recordings exist.

**Decision requested:** approve stage A's routing correction, and choose whether
to pursue the proposed directed adaptive profile (new `/sync/query`) or first
qualify the simpler shared 0.5 Hz profile. No implementation follows this
proposal until Bob rules on that scope.

## Ruling — Bob, 2026-10-04

**Stage A approved; stage B deferred.** After the lead's summary in session
(recommending A now, B only if a real installation shows sync traffic still
matters, with the cheap shared 0.5 Hz ping worth trying during a hardware
timing session): *"approve A. defer B."*
