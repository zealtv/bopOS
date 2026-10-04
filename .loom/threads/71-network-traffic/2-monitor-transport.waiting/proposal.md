# Monitor transport — proposal for Bob

**Recommendation:** make raw OSC a per-window subscription, selected by the
visible Incoming/Outgoing panes and filtered at the server. Send bounded
100 ms batches instead of one WebSocket message per OSC tap. Keep normal
control/state convergence independent of the console; coalesce visual updates
and fix the socket's unbounded buffering of events with no handler. Reuse this
transport for the coming Modules panels, above 59/8's existing leased stream.

At 50 simulated nodes, one client received **312 WS messages/s with static
points, 362/s with a moving point**; three moving-point clients received about
**1,048/s combined**. The default raw console could be quiet except for ordinary
commands/results, with high-rate traffic represented by rate summaries. Raw
sync/heartbeat/point lines would remain available by explicit selection.
**That default visibility change, subscription history/Pause behavior and the
proposed labels below need Bob's ruling.** This is proposal only: no runtime,
OSC-contract or port changes, no implementation or commit.

## Evidence: what actually reaches every window

`OSCBridge._send_to()` taps every successful outbound send as `osc_out`;
`handle()` taps every received message as `osc_in`, even if later ignored.
Both call `Dashboard.queue_broadcast()`, which creates an asyncio task per
publication. `Dashboard.broadcast()` then awaits `send_json()` on each client
in turn. Independent broadcast tasks can overlap; there is no per-client
queue cap, sole writer or slow-client deadline in this path.

The Monitor formats every tap, retains 500 lines per direction and renders
the last 200, throttled to 150 ms. The default text filter is empty. The dock
starts collapsed; collapse, inactive panes and Pause do not stop reception.
Pause freezes rendering while the rolling history continues to change.
Text filters run on already-delivered formatted lines, including timestamp,
address, arguments and peer. Thus a hidden console saves no network or parsing.

Other publications deserve separate treatment:

| Type | Current producer | Current rate/cost at 50 assigned nodes |
|---|---|---|
| Raw `osc_in` / `osc_out` | Every receive/successful send | Nominal 202/s for sync alone: 2 pings, 100 pongs, 100 offsets. Plus heartbeats and other traffic. |
| `sync` | Accepted pong, throttled to ≥200 ms per UID | Approximately 100/s at today's 2 Hz probes. Device sync facts are updated too. **No shipped JS `sync` handler was found.** |
| `heartbeat` | Every received `/hb` | Nominal 5/s with this harness's assigned-node ten-second heartbeat interval. This is a second publication beside its raw tap. |
| `device_update` | Changed heartbeat fields and other state changes | **Not unconditional on every beat.** Heartbeat comparison covers ID, IP, version, engine-alive, RSSI, online and assignment revocation. Simfleet randomly varies RSSI, so many beats cause a full enriched device projection. |
| `point_frame` | Dashboard's moving-point loop | Nominal 25/s while any point moves; zero for a static set. Each moving tick also emits one raw `/pt` tap. Neither stream is multiplied by node count. |

The 71/1 unicast-offset routing correction would not itself reduce these tap
counts: every offset still exists. Adaptive clock polling would reduce them,
but Monitor transport should be bounded independently of that decision.

### Localhost measurement, with actual WebSockets

`measure_monitor.py` imports the production dashboard, runs its OSC loops and
its production WebSocket handler, and connects real transport clients to a
loopback-only server. Fifty assigned simfleet nodes use the default ten-second
heartbeat interval, no Pd and no network loss injection. After twelve seconds
of acquisition, each phase has three seconds of settling followed by twelve
seconds of counting. Connect snapshots/inventory work are excluded. The point
fixture is one orbit; clients continuously drain, without browser rendering.
WebSocket compression is disabled, so bytes below are uncompressed JSON bytes,
not TCP, WebSocket-header or Wi-Fi airtime bytes.

| Phase | Raw tap publications/s | All queued publications/tasks/s | Received WS messages/s per client | Combined WS messages/s | JSON B/s per client |
|---|---:|---:|---:|---:|---:|
| No clients, static points | 206.15 | 314.31 | — | 0 | — |
| One client, static points | 201.71 | 311.78 | 311.78 | 311.78 | 56,407 |
| One client, moving point | 230.25 | 361.66 | 361.66 | 361.66 | 57,429 |
| Three clients, moving point | 218.30 | 349.86 | 349.36 | 1,048.08 | 63,393 |

Publication and receive windows can differ at their edges (six messages per
client in the final phase). These counts are not a UDP/WS loss estimate. The
short windows contain one or two heartbeat rounds and jittered sync probes;
compare them with mean-rate calculations rather than extrapolating every
decimal. Moving-point ticks measured ~24.08 Hz rather than ideal 25 Hz.

For the one-client moving phase, each second contained about 126.08 outgoing
taps, 104.17 incoming taps, 100 `sync`, 24.08 `point_frame`, 4.17 `heartbeat`
and 3.17 `device_update` messages. All captured raw taps in these settled
fixtures were sync, heartbeat or point traffic; ordinary command/error/show
traffic would still appear in real use. With no clients, ~314 tasks/s were
still created to publish to an empty client set.

The JSON and `ws-observations.jsonl` retain 12,275 received messages from the
first client of each connected phase; all three clients have independent
count/byte totals. Runtime source hashes were unchanged during the run.
This measures software transport, not browser CPU/heap, slow-client saturation,
Wi-Fi or physical fleet behavior. Batched/subscribed performance is a proposed
bound, not an implemented benchmark result.

### A second bound is needed in `ws.js`

`BopSocket.emit()` appends every event with no registered handler to
`pending[type]`, with no size/age limit. Snapshots correctly retain only the
latest per type. The main app has no `sync` handler; standalone Remote has no
raw-tap handlers either. This bypasses the Monitor's 500-line bound.

`check_pending.cjs` replays the retained messages through the **shipped**
socket implementation, with inert callbacks for the observed handled types.
It leaves 3,453 `sync` records pending in the main socket. With Remote's actual
registered event types, it leaves 12,077 records: raw incoming/outgoing,
heartbeat, sync and point frames. This is an object-count demonstration of
the buffering path, not a browser heap-byte measurement.

## Proposed transport

### Subscribe only to work that the window consumes

Add a dashboard-internal WS subscription message replacing that connection's
complete current selection. Suggested fields: generation, active raw
directions, exact device UIDs, literal address include/exclude prefixes and
enabled high-rate classes; Modules adds its source UID and selected names.
This is a proposal for the dashboard API, **not a new OSC address or port**.
Cap filter lists (e.g. 16 UIDs and 16 prefixes, 128 characters per prefix),
validate fields, and reject an invalid replacement without changing the old
selection. Do not accept arbitrary client-supplied regular expressions.

For raw OSC, expand/collapse and both split panes determine interest; subscribe
to the union of visible Incoming/Outgoing panes, not just one global active
tab. Pause, inactive pane, collapsed dock, document hidden or disconnect
releases that raw interest. Another window's subscription is independent.
Reconnect starts unsubscribed and resends the current UI selection after the
handlers are installed. Generation acknowledgements let the browser discard
old in-flight batches after a filter/source change. Do not replay hidden-period
history or pretend the local 500-line buffer is a recording.

The existing free-text filter should remain a local search over retained
lines, with today's case-insensitive wildcard/AND/negation semantics. Add
separate structured transport filters for direction/address/device. Moving
the existing field to an address-only server filter would silently change its
argument/peer/timestamp search and retroactive-history behavior. Clearly label
that server filtering determines what can enter history at all.

Resolve a tap's exact UID only when its payload, concrete selector or request
context establishes it. A shared source IP is insufficient (simfleet and
virtual relays share one). Fleet/group outbound messages match selected devices
when their recipient scope intersects the selection. Unknown attribution is
reported separately; a UID-filtered view excludes it and shows its count,
rather than guessing an identity or claiming a complete device audit.

### Filter before preparing a console record

Use address/direction classification and subscriber interest before console
argument conversion, JSON serialization, queueing or task creation. With no
raw subscribers there are no tap publication tasks or raw WS messages. Cheap
class/direction counters may still feed an active summary. Keep normal OSC
handling, UDP sends, state updates and Wi-Fi secret redaction intact; a hidden
console must not disable an administration reply or safety/error notice.

Proposed raw classes:

| Class | Raw default | On-demand representation |
|---|---|---|
| `/sync/ping`, `/sync/pong`, concrete `/<id>/sync/offset` (and any later ratified sync probe) | Off | One-second direction/rate summary; opt in to individual lines. |
| `/hb` | Off | One-second counts/rates; opt in to individual lines. Normal online state and heartbeat indicators still work. |
| `/pt` and `/pt/*` | Off | Counts/rates and latest map geometry; opt in to raw frames/clears. |
| Ordinary commands, events, probes, reports, receipts and errors | On in an active raw pane | Existing timestamp/address/arguments/peer lines, subject to the selected server filters and explicit bounds. |
| IO poll values on 5551 | Not added to the generic raw tap | Selected Modules panels, using the stream's consumer seam. No always-on blob/log fan-out. |

Counts suppressed by selection are **filtered**, not dropped. A default rate
summary should say what classes are excluded and provide an explicit way to
include them. Proposed wording/control names are subject to Bob's ruling.

### Batch and bound each connection

One client writer owns its socket, with a 100 ms telemetry flush; no task per
datagram per client. Combine raw records and subscribed visual telemetry into
one envelope per flush, and dispatch its entries through the existing browser
handlers. Preserve order between Incoming and Outgoing records within the
tap sequence. Snapshots and command/safety results get priority, outside the
telemetry cadence; they are not raw-console records and must not be sampled.

Suggested initial policy constants (documented, tested, subject to tuning):

| Resource | Proposed bound / overflow behavior |
|---|---|
| Per-client raw pending history | 500 records **and** 128 KiB, whichever comes first; discard oldest matching unsent records to retain recent activity. |
| Raw admission | 500 matching records/s, burst 500. Above the limit, count omitted matching records explicitly. |
| Batch | At most 100 raw/sample records and 32 KiB encoded telemetry, both enforced; ≤10 telemetry messages/s/client. Excess entries wait for later ticks within their caps, without unbounded frame splitting. |
| One console record | 4 KiB encoded preview; visibly mark omitted argument bytes and count truncations. Do not send an unbounded blob/string because only 500 rows are retained. |
| Writer | One in-flight send and one bounded pending telemetry envelope; a two-second send deadline closes only that slow connection and releases its subscriptions. |
| Core control queue | Separate bounded priority lane, initially 256 messages/512 KiB. On overflow close/reconnect with snapshot convergence; do not silently drop a mutation result or replace it with success. Large snapshots need their own explicit tested size limit, not the 32 KiB telemetry limit. |

Report per-subscription, per-channel `dropped_since_subscribe`, plus interval
delta, truncations, intentional coalescing and filter counts. Counters travel
in a fixed-size status field, outside the row quota, even when no rows fit.
Render a visible persistent indicator and a synthetic gap line before the
next delivered rows: proposed text **“N matching messages dropped”**. Clear
has defined local-history/counter-reset semantics; reconnect resets the
subscription generation and reports the discontinuity. This is not an audit
log, and an unacknowledged socket close cannot establish exactly how many
in-flight rows the browser missed.

Each client owns its own counters and buffers. One client selecting everything
or draining slowly must not block OSC, state mutation or another client's
writer. Do not accumulate flush tasks while a writer is blocked. The batch
byte budget includes envelope/counters/metadata, not merely payload values.

### Coalesce visual state without losing control results

Keep initial `state`/`distribution`/Show snapshots and `SNAPSHOT_TYPES` replay
behavior. Do not gate core installation state on Monitor visibility.
Heartbeat updates can retain latest time per UID per 100 ms; changed device
projections can retain latest per UID/generation, enriched **once at flush**.
Offline/removal, errors, probe/command results and Show transitions preserve
order and priority. A removal invalidates pending device updates so an old
batch cannot recreate a card. Keep the existing execution-mode/generation
guards when devices are replaced.

Rotate retained UID updates fairly across byte-limited batches; a large fleet
may require several ticks. Oversized core projections use the bounded priority
lane, not a truncated state object. The cadence is a scheduling target, not a
promise that every visual update arrives within 100 ms under overload.

For a client drawing the map, send latest `point_frame` at up to 10 Hz; static
geometry remains change-driven. **Do not change the 25 Hz OSC point loop or
engine input.** Remote, which has no map handler, needs no point-frame feed.
Replace the currently unconsumed per-pong `sync` WS event with an explicitly
subscribed one-second System/clock summary using current backend facts; merge
needed facts into the installation store. Keep today's “settled” definition
(sample count), without claiming it proves physical timing quality.

Bound non-snapshot, pre-handler buffering in `BopSocket`: for example 50
records/64 KiB total with a five-second lifetime, with diagnostic overflow
counts. Streaming subscriptions must install handlers before starting, and
unsolicited unconsumed stream types are not retained. Snapshot replay remains
latest-per-type. The browser's 500 retained/200 rendered console limits remain
useful after server admission; neither bound substitutes for the other.

Under the measured quiet moving-point workload, removing default high-rate
raw lines and per-pong `sync` already removes ~330 of 362 messages/s. Combining
subscribed map/device/heartbeat updates in a 100 ms envelope gives a proposed
**≤10 telemetry messages/s per window**, plus priority snapshots/results and
occasional status traffic. This is a frame-rate bound, not a measured latency
or byte-saving percentage; verbose raw selection retains more bytes and may
hit the explicit row/byte caps. Three clients would ordinarily receive ≤30
telemetry messages/s combined instead of the measured ~1,048 total, with core
control messages added as needed.

## Modules (59/9): use the same mechanism above the leased source

Ratified 59/0a §§4–5 puts interactive panels only in the Monitor dock's
**Modules** tab, with “Show in Monitor”, one component and an ordinary browser
pop-out. Inputs retain the driver's units and values; Live controls write to
the module, while simulation reverses the arrows. Those decisions remain the
foundation, not a separate sensor-debug console or streaming service.

59/8's source already provides `subscribe_io(uid, consumer, callback)` /
`unsubscribe_io(uid, consumer)`: one shared device, renewal every three
seconds, ten-second node/bridge leases, no consumers means close, Performance
means stop. The current main-checkout integration exposes that seam. This
proposal does not change its OSC blob, ownership, ports or refusal semantics,
and no sibling worktree was inspected or modified.

Give each window's selected module panels a server consumer identity tied to
its connection/generation. Subscribe once to the selected device, filter module
names at the server, enqueue **ordered sample batches** into the same bounded
writer, and release on uncheck/disconnect. Source samples remain untouched;
do not round values to save bytes or turn panels into all-browser raw tap
traffic. Preserve module identity and sample ordering, attach leader receipt
time, and retain original bundle timetags where present; do not invent a
node acquisition timestamp that the source wire does not carry. Share the
source with a Patch Edit consumer; stopping a visual subscriber must not close
the source while the editor still needs it. A second device remains rejected
locally while the first has consumers, with an explicit busy result; a new
window must not silently steal another consumer's source.

Suggested panel queue: at most 100 original poll bundles/128 KiB per client,
subject to the shared encoded batch/writer limits. Drop oldest complete visual
bundles on overflow and count them separately from raw console lines; never
claim every short press was observed after a gap. Render latest numeric values
at paint cadence, but inspect all delivered samples for transient touch rails
so a press/release inside one 100 ms batch is not discarded by latest-only
coalescing. Do not add the deferred min/max/swing window feature by implication.
Driver descriptions still determine channels/units/ranges and output controls.

The **editor's engine input path must stay at original poll rate with original
bundles**, independent of lossy visual queues and paint cadence. UI writes
still use the existing administrative path and receipts; batching must not
coalesce distinct output commands or change Performance behavior.

For hidden/collapsed module panels, propose suspending **visual** subscriptions
while remembering the checkbox selection; reopening resumes. This extends the
ratified checkbox workflow and needs Bob's explicit approval. Editor selection
remains a separate consumer. No high-rate module data should accumulate in
`ws.pending` in a hidden pop-out or in a window with no panel.

## Every operator-visible change requiring Bob's ruling

| Proposed change | Today's behavior / consequence |
|---|---|
| Exclude raw sync, heartbeat and point classes by default; show rates with explicit opt-in | Empty filter currently shows every tap. This changes the initial console contents. |
| Capture raw history only while its pane is visible/subscribed | Today opening a pane can reveal traffic collected while it was hidden/collapsed. New view begins at subscription. |
| Pause suspends capture, Resume resumes without backlog | Today only rendering pauses and the last 500 records keep rolling. Show the pause gap explicitly. |
| Add structured server filters, with named high-rate controls and exclusion summary | Existing free-text search stays local; server-excluded history cannot be recovered by editing it. Proposed names/wording need approval. |
| Visible per-window drop/truncation/gap indicator | Current 500-row eviction has no such explanation; this makes loss explicit. |
| Visual heartbeat/device/map updates use 100 ms batching; map paints up to 10 Hz | Current moving map receives ~25 Hz. Byte limits/backpressure may require more ticks. Audio/point OSC rate is unchanged. |
| System clock count refreshes through a one-second consumed summary | Per-pong sync events currently have no handler; System otherwise learns updated device facts through other projections. No new claim that “settled” means measured accuracy. |
| Hidden module panels suspend their visual consumer but retain selection | Extends the already-ratified “Show in Monitor” workflow; editor consumers keep their stream. |

A simpler first delivery could preserve raw default classes and subscribe
whenever the dock is expanded, then add high-rate exclusions after Bob chooses
them. It still needs a ruling on hidden-history/Pause semantics. The per-client
queue/writer bounds and unhandled-event fix are useful under either choice.

## Alternatives rejected or deferred

| Alternative | Why it does not solve the whole problem |
|---|---|
| Only throttle DOM rendering or cap browser history | Already done. All JSON still crosses the socket; unhandled events bypass the console ring. |
| Batch every tap to every window | Cuts frame count, but keeps byte fan-out and hidden work. Useful only alongside subscriptions/filtering. |
| Spawn parallel client send tasks / `gather` each publication | Removes one sequential await but leaves task/queue growth unbounded and no slow-client isolation. |
| One global tap ring or global Pause/drop count | A noisy client's choices affect others, and loss cannot be attributed to a particular window. A historical recorder would be a separate feature. |
| Sample all event types uniformly | Loses command receipts, errors and transient presses; full state and event streams have different semantics. |
| A new module socket/service or stream per browser | Duplicates subscription/backpressure logic and fights the ratified shared one-device lease. Use one dashboard WS and the existing IO consumer seam. |
| Move the existing text filter entirely to address prefixes | Breaks argument/peer/time search and filtering of retained history. Separate capture selection from local search. |

## Code cost and implementation gates

**Medium, dashboard-only:** a per-client broker with a sole bounded writer,
subscription validation/generations, class counters, lazy tap preparation and
visual-state coalescing; subscription/batch dispatch in `ws.js`; Monitor pane,
split, Pause, visibility, filtering and gap UI; focused tests. Preserve Wi-Fi
redaction, snapshots, core ordering and current error/status surfaces. No
node, Pd, LAN OSC, poll-rate or port change is needed for this transport work.
Modules then adds one adapter and UI consumer to that broker above 59/8,
not another transport. Follow-up patches can separate raw admission/writers,
state coalescing, and Modules integration without losing their shared bounds.

Verify the implementation with the same 50-node fixture plus 100-node/stress
fixtures: no raw frames/tasks when unsubscribed, filter correctness (including
shared IP/unattributed replies), two active panes, independent clients,
explicit high-rate opt-in, exact limits/counters, 100 ms batch cadence and
redacted/truncated payloads. Deliberately stall one writer and flood raw/module
traffic; show bounded memory/tasks, continued OSC/control work and normal
delivery to a healthy client. A fast-draining localhost run cannot establish
those failure properties.

Browser journeys must check hidden/collapsed/Pause/resume, reconnect generations,
retained text filtering, visible loss, Remote's unhandled-event bound, map
cadence and tombstone ordering. For 59/9 include dock/pop-out reference counts,
busy second-device selection, Performance, source expiry, output receipts,
short press/release within a batch, and unchanged original-rate editor input.
Measure browser heap/CPU over at least ten minutes before claiming an
improvement, then compare on Bob's ordinary laptop/tablet and real Wi-Fi rig.
Hardware module/audio fidelity remains a separate physical check.

**Decision requested:** approve the visible-default table, or select the
conservative first delivery preserving raw classes. Proposed internal API
names, controls and gap text are suggestions, not ratified UI or wire tokens.
