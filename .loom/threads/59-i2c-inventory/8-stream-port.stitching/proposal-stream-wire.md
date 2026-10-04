# Stream wire details — ratified (59/8)

2026-10-04. Ratified by the instruction to implement 59/8 per this proposal
and the original brief. The matching shipped text is in OSC-CONTRACT §6.

The ratified design specifies `/os/io-stream <uid> <ok|err> <json>` and
`/io/stream <uid> <bundle…>` but does not specify the JSON fields or OSC
encoding of the embedded bundle. The task brief explicitly requires stopping
for genuine wire ambiguity. The following fills those gaps without changing
the ratified ports, ten-second lease, poll-rate limit or Performance refusal.

## Receipt

Proposed JSON has exactly two fields: `active` (boolean, the node's current
lease state) and `error` (null, `performance`, or `invalid-arguments`).

| Request/result | Status | JSON |
|---|---|---|
| Development: `1`, open or renew | `ok` | `{"active":true,"error":null}` |
| Development: `0`, close, including already closed | `ok` | `{"active":false,"error":null}` |
| Performance: valid `0` or `1` | `err` | `{"active":false,"error":"performance"}` |
| Anything other than one OSC integer `0` or `1` | `err` | `{"active":<current boolean>,"error":"invalid-arguments"}` |

Malformed requests do not change the lease. Entering Performance closes it
immediately. These administrative refusals never change module state or emit
`/os/io-error`. The ten-second duration is fixed by the contract, so the
receipt needs no time field. Receipts use the existing requester reply path;
value packets alone use 5551.

## Value packet

Proposed LAN message: `/io/stream <uid:string> <bundle:OSC blob>` (typetags
`,sb`), sent to the requesting host's IP address on UDP 5551. The blob contains
one complete, encoded OSC bundle copied from the bridge's poll result. Its
module addresses, argument types, ordering and bundle boundary are preserved.
There is one outer message per poll bundle, at most the bridge poll rate.
The dashboard decodes the blob for subscribers; the future editor feed can
forward those original bundle bytes to 6662.

The localhost value packet on 7771 remains the original OSC bundle, matching
the ratified requirement to copy it there. It is distinct from localhost
control replies. No value packets go to the fleet control or heartbeat ports.

## Lease owner and bridge command

Proposed owner rule: the most recent successful `io-stream 1` sets the sole
destination and renews the ten-second lease. A request from another host
replaces that destination; it does not create a second stream or introduce a
new `busy` refusal. In Development, `io-stream 0` closes the sole lease,
regardless of requester. The dashboard subscription manager allows consumers
of one device at a time; attempts to subscribe to a second device while the
first still has consumers fail locally without a new wire token.

Proposed bridge command on localhost 8880: `/io/stream <0|1>`. `1` enables or
renews copying for ten seconds; `0` disables it. The node renews this with each
successful administrative renewal and sends `0` on close, expiry or entry into
Performance. The bridge's own timeout also bounds copying if the node stops.
This requires reserving the module name `stream`, alongside existing bridge
verbs. The engine's ordinary bundle delivery to 6662 continues throughout.

The user authorized implementation of these details on 2026-10-04.
