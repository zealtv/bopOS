# 2-macos-osc-routing-shutdown

Make Dashboard → physical-device OSC usable on the active macOS LAN and make
transport failure non-fatal to both heartbeat processing and application
shutdown.

## Current failure

- `dashboard/server.py:2455` defaults `--osc-target` to
  `255.255.255.255`.
- `dashboard/osc_bridge.py:126-127` creates a broadcast-capable but unbound UDP
  sender.
- On the incident Mac, that socket raises
  `OSError: [Errno 49] Can't assign requested address` for limited broadcast.
- The same socket succeeds after binding to the active LAN address
  `192.168.0.100`; subnet broadcast `192.168.0.255` and Imani unicast
  `192.168.0.103` also succeed.
- `_send_to()` lets the exception escape. During first discovery that can abort
  the rest of heartbeat handling after the in-memory record has been partly
  updated. During `Dashboard.stop()`, `stop_supervisor()` unnecessarily
  restores live master/mute state even when the supervisor is already off; the
  exception prevents task cancellation, OSC close, and `state.close()`.

## First: bounded archaeology (timebox it)

Bob onboarded fresh devices from this Mac at least three times before
(Finn Jet and Ciro Toast reflashes, Ciro fresh through bopOS) without hitting
this, and on 2026-07-26 ruled out environment drift: same machine, same local
network, no known OS/VPN changes, no flags on his own `./run.sh` runs. See
"Prior successful onboardings" in `../diagnosis.md` for the full evidence.

The working hypothesis is therefore **latent fault, not fresh regression**:
this Mac likely never routed unbound limited broadcast (errno 49 was recorded
for it on 2026-07-11), and the earlier onboardings succeeded because their
traffic took routable paths — pre-`5eda7b4` `uid_command` followed the mutable
execution destination (loopback during simulation), and the Finn/Ciro
verification sessions were launched by loom harnesses with explicit
ports/targets rather than Bob's bare `./run.sh`.

Spend a bounded pass confirming or refuting that reading:

- Trace where first-seen/enabled/UID-admin sends went before vs. after
  `5eda7b4` ("Separate physical device control routing").
- Check the tied Finn/Ciro verification artifacts and handoffs for how those
  sessions actually launched the dashboard (`--osc-target`, ports, mode).

Record the finding in the stitch notes. It decides what the regression test
pins (a routing code path vs. a long-standing masked hazard). Do not let the
archaeology block the fix — the design below is correct under either reading.

## Prescribed design

Three parts. None is a workaround; `--osc-target 192.168.0.255` dies with this
stitch.

### 1. Self-locating sender: bind the source, keep the target

The diagnosis's probe table proves that binding the sender to the active LAN
source address makes limited broadcast routable on this Mac. So:

- Keep `255.255.255.255` as the default `--osc-target`. The ratified
  selector/broadcast wire model does not change.
- **Split the sender by destination, not by route name.** There is currently
  one shared `self.sender` behind both `send()` and `send_physical()`; binding
  it to the LAN address risks the loopback path in simulation/edit mode. Do
  not split it as "physical socket vs execution socket" either — in Live mode
  the execution destination *is* the physical destination. Key the choice in
  `_send_to()` on the destination itself: a LAN-source-bound socket for
  non-loopback destinations, an unbound (or loopback-bound) socket for
  loopback destinations.
- **Discover the LAN source address by probing toward a known device.** The
  asyncio receive callback yields the *peer* address only (the local receiving
  address would need `IP_RECVDSTADDR`/pktinfo plumbing — don't add it).
  Instead, on heartbeat, UDP-connect a throwaway datagram socket toward that
  device's source IP and read `getsockname()`; bind the LAN socket to the
  result. First-seen sends only ever happen in response to a heartbeat, so a
  device IP is always available at the moment discovery is needed. Discover
  lazily on first need, cache the result.
- Handle re-binding on network change explicitly: if sends start failing and a
  fresh probe yields a different source address, rebind and retry later
  sends. Keep it simple — lazy re-discovery on failure, not an interface
  watcher.
- `--osc-target` continues to accept explicit unicast/broadcast for tests,
  simulators, and unusual venues; loopback and Linux/Pi behavior stay intact
  (the destination-keyed split must be a no-op improvement there, not a
  regression).

### 2. Transport fault boundary in `_send_to`

- Catch `OSError` in `_send_to()`; a failed send becomes an operational
  signal, not control flow.
- **Precise browser contract:** broadcast a new `osc_transport_error` event —
  address, destination, errno/message, timestamp — throttled by
  `(destination, errno)`. The Monitor's System stream renders it; the client
  side of that contract is part of this stitch. `osc_out` stays success-only:
  the console tap must not record a datagram that never left.
- Guard the error broadcast the same way the existing tap guards
  `RuntimeError` — sends can legally happen before the asyncio loop exists.
- Incoming heartbeat processing, first-seen requests, and later retries
  continue past a failed send — a heartbeat must always produce a complete
  public device/update, never a half-processed record.

### 3. Exception-safe shutdown that sends nothing it doesn't need

- `stop_supervisor()`'s already-off branch stops replaying live master/mute
  state — closing an already-Live dashboard is a no-op, not a broadcast.
- Structure `Dashboard.stop()` so every stage runs regardless of earlier
  failures (task cancellation, `osc.close()`, `state.close()`); where a final
  send is genuinely required, its failure must not escape the cleanup
  boundary. Ctrl-C reaches Uvicorn's clean application shutdown even with the
  route unavailable.

## Verification

- Focused Python living tests under `tests/`:
  - a sender stub raising errno 49 → a device heartbeat still becomes a
    complete public device/update, the failure surfaces as an
    `osc_transport_error` event throttled by `(destination, errno)`, and
    `osc_out` records nothing for the failed datagram;
  - Dashboard shutdown reaches task cancellation, OSC close, state close, and
    a clean application-shutdown result when `sendto` fails;
  - already-off `stop_supervisor()` emits no OSC;
  - destination-keyed socket split: with the LAN socket bound, loopback-bound
    destinations still route through the unbound/loopback socket (simulation
    and edit-mode sends unaffected);
  - source-address discovery: assert the *selection logic* (probe toward the
    heartbeat's device IP, cache, rebind-on-failure) with fakes — do not
    assert that a real limited-broadcast send succeeds in CI, and do not
    depend on the incident subnet. The real send is the hardware adoption
    check below.
- Run adjacent dual-route, execution-target/simulation-transition, device
  control routing, and clean-shutdown regressions selected from living tests
  and the most relevant tied verification artifacts.
- Record the archaeology finding (which of the three explanations held) in the
  stitch notes, and pin it in a test if it was a code-path change.
- Hardware adoption: with Imani Silver online, launch with the **default**
  target (no `--osc-target`), confirm first-seen report, patches, assets,
  Device enabled state, assignment, and at least one safe administration
  request round-trip. Record the Mac interface/address, discovered source,
  destination, command, receipt, and limitations.
