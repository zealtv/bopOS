# Monitor capture and dashboard transport

The Incoming and Outgoing panes capture only while visible and unpaused.
Both visible split panes contribute to the window's selection. Collapsing the
dock, changing panes, hiding the document or disconnecting suspends raw capture;
opening or resuming starts a new capture period without hidden-period history.
Each window has its own selection, buffers and counters.

Ordinary commands, receipts and errors are included by default. Raw sync,
heartbeat and point traffic is excluded, with observed rates refreshed each
second. **Capture filters** enables those classes and accepts literal address
include/exclude prefixes and exact device UIDs. These filters determine what
can enter history. The separate retained-lines search still searches timestamps,
arguments and peers, case-insensitively, with wildcard/AND/negation semantics.
Filters apply to both console panes. An invalid replacement keeps the previous
acknowledged selection and displays the refusal.

Attribution uses explicit UID payloads, concrete selectors and fleet/group
recipient scope, never shared IP alone. Unknown attribution is counted as
unattributed and excluded from a UID-filtered view. This is an observation
console, not a complete device audit or recording.

The browser retains 500 lines per direction and renders at most 200. These
remain useful local history limits; their normal oldest-line eviction is not
transport loss. Transport drops and shortened previews have a persistent
indicator. Before the next delivered rows, a gap line states how many matching
messages were dropped. Intentionally excluded traffic is **filtered**, not
dropped. Clear removes that pane's local history and resets its displayed
drop/truncation baseline; it does not change capture or cancel records already
in flight. A selection change resets server counters and is marked in history.
Reconnect starts a new generation and marks an unknown discontinuity; it does
not claim to count all rows lost with a closed socket.

## Dashboard-local WebSocket API

`capture_selection` replaces the connection's complete selection. It is not
an OSC address, node command, or port change. Send it after installing stream
handlers. Fields:

```json
{"type":"capture_selection","data":{"generation":1,
 "directions":["in","out"],"uids":[],"include":["/os/"],"exclude":[],
 "classes":[],"map":true,"clock":false,"modules":null}}
```

Generations are increasing nonnegative JavaScript-safe integers. Directions
are `in`/`out`; classes are `sync`/`heartbeat`/`points`. Each UID or prefix list
has at most 16 entries, each at most 128 characters; prefixes start with `/`.
No regular expressions are evaluated at the server. `capture_status` confirms
the accepted generation. Refusals include the accepted generation, rejected
`requested_generation`, and an error; no selection is partially applied.
Reconnect begins unsubscribed and the browser resends its current selection.

`telemetry` has `data: {generation, status, entries}`. Entries are ordinary
`{type,data}` messages dispatched through existing handlers. The browser drops
old-generation envelopes. Status has per-channel (`in`, `out`, `modules`,
`visual`) drop totals/deltas, filtered/unattributed/truncated/coalesced counts
as applicable, plus one-second observed direction/class rates. Status is
included in the byte budget and does not use the row quota.

Device and heartbeat projections coalesce by UID. A shared 100 ms loop enriches
each changed device once for all windows. Retained UIDs rotate ahead of newly
changed ones, and raw/sample/state lanes share the batch budget. Removal,
offline and full snapshots invalidate older queued projections, including
prepared envelopes, while retaining unrelated raw observations. Core snapshots,
administrative pending transitions, command results, errors and Show transitions
use the ordered priority lane. Enrichment retains device-identity guards.

Installing a `point_frame` handler requests map frames, with latest values at
up to 10 Hz. Remote installs no map handler and receives no frames. Static
geometry remains change-driven. The OSC point loop still runs at 25 Hz.
Visible System panes request `clock_summary` once per second; its current backend
sync facts merge into the installation store. “3+ samples” describes acquisition
count, not measured physical timing accuracy. Per-pong `sync` WS events are gone.

## Bounds and overload

| Resource | Limit and behavior |
| --- | --- |
| Raw unsent records per connection | 500 records and 128 KiB encoded; drop oldest matching records |
| Raw admission | 500 matching records/s per connection, initial burst 500; filter changes do not refill the burst; count excess matches |
| Raw preview | 4 KiB encoded; shorten strings/omit blobs or values visibly after Wi-Fi redaction |
| Telemetry envelope | 100 entries and 32 KiB including status/metadata, at most one per 100 ms tick |
| Socket writer | One task/connection, one in-flight send, one pending telemetry envelope; 2 s deadline closes only that connection |
| Priority control | 256 queued messages; 512 KiB for nonsnapshots; overflow closes for reconnect convergence instead of silently losing a result |
| Full snapshots | Each at most 4 MiB; total priority queue at most 8 MiB, including snapshots |
| Visual IO samples | 100 complete selected poll bundles and 128 KiB encoded; drop oldest bundles, count separately; oversized visual bundles are dropped whole |
| Browser pre-handler events | 50 records and 64 KiB total, 5 s expiry, diagnostic `pendingDropped`; unconsumed streams are discarded |

Oversized device/clock projections enter the priority lane whole, subject to
its cap. One blocked writer cannot create flush tasks, grow its queues without
bound, or prevent other windows and OSC processing from progressing. The
100 ms cadence is a scheduling target; a large fleet or overload can defer
visual updates. Core overflow/deadline closes with code 1013 and releases the
connection's source consumers. Browser snapshot replay remains latest-per-type.

## Seam for Modules (59/9)

The live panel component (`module-panels.js`) installs its
`io_samples` handler, then replaces `modules` with
`{"uid":"…","names":["touch","adc"]}` (at most 64 names, each 128 characters).
Sending `modules:null` releases its visual consumer. Hidden/collapsed panels
must retain their checkbox choice locally while sending no visual interest;
reopening requests it again. The server identifies the consumer by connection,
shares 59/8's `subscribe_io` source with editor consumers, and never steals a
second device. Busy/Performance refusals leave the prior selection intact.
Disconnect releases visual ownership. Entering Performance releases it and
discards queued visual samples; resuming requires a fresh panel selection.

`io_samples.data` carries UID, selected module names and original values,
leader `received_at` seconds, and the original OSC bundle `timetag` as eight
hex-encoded bytes. Each entry represents one original poll bundle in order;
there is no invented node acquisition time or value rounding. Inspect every
delivered bundle for short press/release transitions before painting latest
numeric values. Gaps do not establish that every transient was observed.
An unencodable visual bundle (for example nonfinite JSON numbers) is dropped
whole and counted; its original editor callback remains independent.
The editor's original-bundle/original-rate consumer remains independent of
the visual queue; administrative writes still use existing receipts.

Implementation: `dashboard/monitor_transport.py`, `ws.js`, `monitor.js`.
Software checks: `test_monitor_transport.py`, `verify_monitor_transport.py`,
the fast/browser suites, and the 50/100-node loopback measurement in 71/2.
Browser CPU/heap over ten minutes and Bob's laptop/tablet/physical Wi-Fi rig
remain separate verification before making those performance claims.

Device-tab module choices belong to each browser window and reset on reload;
a pop-out URL restores its explicitly selected panels. The
Device inventory checkbox reveals Modules and names the source in each panel.
Panels retain at most 120 values per described input. Every delivered original
poll is inspected before a single animation-frame paint; suspension, reconnect
and reported drops break the trace. Numeric text formats floats to at most six
significant digits with trailing zeros dropped, matching Pd's %g-style display;
integers and stored sparkline samples retain their original precision. The full
module OSC address/value list sits alongside the unit-bearing channels.
Output forms come from driver command/argument descriptions; results remain on
the existing administrative receipt path. Performance disables the controls and
the dashboard independently refuses forged `io_write` commands.

Pop-out opens an ordinary same-origin browser window running the same dock and
panel component. A panel moves its visual interest to that window; a dock pop-out
collapses its source dock. Closing the new window restores the source view. Each
window releases its consumer when hidden or disconnected, and the source lease
still expires independently if a window or the dashboard disappears.
