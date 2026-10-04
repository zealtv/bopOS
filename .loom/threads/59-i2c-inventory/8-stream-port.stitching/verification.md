# Verification — 59/8 stream port

2026-10-04. Implemented on `stitch/59-8-stream-port`, based on `c7e7710`
(including manifest modules and the Device-tab IO card). The user ratified
`proposal-stream-wire.md` by directing implementation per that proposal.

## Delivered

- Original poll bundles copy to localhost 7771 only while the bridge's own
  ten-second lease is active. Engine delivery to 6662 is independent.
- Node leases preserve one requester, renew for ten seconds, replace the
  destination on takeover, close idempotently, and expire with a timer.
  The 7771 listener forwards whole bundle bytes inside one `,sb` message to
  the requester's 5551; ordinary control messages retain their dispatcher.
- Performance uses `development_allowed('io-stream', state)`, closes an open
  lease under the mode-transition lock and sends the local close command.
  Both valid stream requests return the administrative `performance` error;
  no module fault or `/os/io-error` is created. Leaving Performance does not
  reopen a stream.
- Dashboard consumers share one device. Open/renew is sent every three
  seconds while consumed; the last release, Performance or shutdown cancels
  renewal and releases consumers. The dedicated IPv4 listener rejects wrong
  source/UID and invalid bundles; values are delivered only to subscribers.
- Simfleet sends changing fake driver-shaped values at its default 10 Hz,
  with lease/destination/Performance parity and generation checks preventing
  an old scheduled sender from reviving a closed or replaced stream.
- Contract §4, §6 (including receipt) and §15, PORTS.md, and current glean
  guidance match the shipped behavior. `stream` is a reserved module name.

## Server API for stitches 9 and 6

Call on the dashboard's asyncio loop:

```python
dashboard.osc.subscribe_io(uid, consumer_key, callback)
dashboard.osc.unsubscribe_io(uid, consumer_key)
```

`callback(bundle_bytes, module_values)` is synchronous. `module_values` maps
module names to their ordered value lists; the original bundle bytes retain
OSC addresses/types and can later be forwarded to an audition engine. Reusing
a consumer key replaces its callback. Multiple consumers of the same device
share the lease. A different device is rejected locally until all current
consumers release it. Performance rejects subscription. No UI consumer is
introduced in this stitch, so normal dashboard startup opens no stream.

## Checks

- `./tools/run-tests.sh fast`: **508 tests passed** (497 existing + 11 stream
  tests). Covers timer renewal/takeover, canceled-timer races, malformed
  requests, expiry, idempotent close, Performance transitions, exact byte/type
  fidelity, independent engine delivery, consumer lifecycle and receipt
  validation. Expected failure-fixture diagnostics are present.
- `tests/verify_io_stream.py`: **passed**. Real localhost bridge/node sockets
  with chip reads faked preserve original bundle bytes, continue control
  scans, and stop copying on expiry/Performance. Real dashboard/simfleet UDP
  verifies one-device/shared-consumer renewal, release, fake values, scans,
  heartbeats, Performance refusal without module faults, and an unrenewed
  lease expiring after the actual ten seconds at no more than 10 Hz.
- `./tools/run-tests.sh browser`: **32/32 verifiers passed**, including the
  new stream journey, existing IO control, Device-tab IO inventory, manifest
  editor, Performance mode and the rest of the browser suite. Full log:
  scratchpad `browser-59-8.log`.
- `git diff --check`: passed. No `.pd` edit, push, merge or loom command.

The socket journey caught a macOS IPv6-only stream bind; the listener now
explicitly binds IPv4, matching the existing control transport.

## Hardware pending

Real Pi/I2C readings, actual bridge copies to 7771 and the requesting host's
5551, cessation on lease expiry/Performance, and continued engine/audio
operation on 6662 remain pending. Local sockets and fake chips/simfleet do
not establish Pi, physical bus or audible performance behavior.
