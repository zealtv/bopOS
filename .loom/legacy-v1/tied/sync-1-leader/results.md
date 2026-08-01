# sync-1 — dashboard as clock leader: results

Implements the leader side of the clock-sync plane pinned in `sync-0`
(`docs/OSC-CONTRACT.md §3.1`). All in `dashboard/` (Python) — no PD, no engine.

## What landed

- **`dashboard/osc_bridge.py`**
  - `sync_ping_loop()` — an asyncio task (started in `OSCBridge.start()`,
    cancelled in `close()`) broadcasting `/sync/ping <seq> <leaderTimeNs>` at
    500±100 ms. leaderTime is echoed by the pong, so the leader is stateless.
    Always on (tight-sync assumes the dashboard runs).
  - `handle_pong()` — on `/sync/pong`: stamps arrival, recovers send-time from
    the echoed leaderTime, `oneWay = rtt/2`,
    `offset = (deviceTime + oneWay) − leaderNow`. Only assigned devices
    (id ≥ 0) are estimated/pushed.
  - `_sync_estimate()` — the smoothing (see decision below).
  - Pushes `/<id>/sync/offset <offsetNs>` once ≥ 3 samples exist; surfaces
    `{offset, rtt, min_rtt, samples, at}` on the device (runtime-only) and
    broadcasts a throttled (0.2 s) `sync` ws message.
- **`dashboard/state.py`** — `sync` added as a runtime-only device field
  (auto-excluded from `durable()`/persistence like `meters`; preserved across
  `load_venue`).

## Implementer's calls (this file is the record)

- **Offset math lives leader-side; the node applies it.** Settled in `sync-0`:
  only the leader sees the round trip, so it owns RTT/offset smoothing; cues are
  broadcast, so each node holds its own pushed offset and converts locally
  (sync-2). `/<id>/sync/offset` is full-state/idempotent; the node slews.
- **Smoothing = low-RTT-band median.** Rolling window of the last
  `SYNC_WINDOW=16` (rtt, offset) samples. The estimate is the **median of the
  offsets whose RTT ≤ 1.5× the window's minimum RTT**, falling back to the whole
  window if that band is empty. Rationale: the lowest-RTT samples suffered the
  least queuing delay, so their `oneWay = rtt/2` symmetry assumption holds best
  (NTP intuition); the median is robust to the asymmetric-delay outliers WiFi
  produces. Samples with `rtt < 0` or `rtt > 200 ms` are discarded outright.
  Cheaper than a full HB rolling regression and good enough for a <10 ms target;
  `sync-3`'s jitter harness is where we measure whether it needs more.

## Verify — `verify_sync_leader.py` (browser-free)

Real dashboard + real simfleet (3 devices, ±30 ms skew, 2 ms pong jitter). A
websocket client reads the leader's `sync` broadcasts; simfleet logs each
device's true skew. Because leader and sim share Linux CLOCK_MONOTONIC, a
correct estimate equals the skew.

```sh
pip install fastapi uvicorn[standard] python-osc websockets
python3 verify_sync_leader.py     # from this stitch dir; locates repo by marker
```

Output (stable across 3 runs, 2026-07-09):

```
[PASS] simfleet logged a skew per device
[PASS] leader estimated every assigned device
[PASS] id=1 estimate converged
[PASS] id=2 estimate converged
[PASS] id=3 estimate converged
[PASS] all estimates within tolerance
[PASS] rtt/min_rtt/samples surfaced
[PASS] set_param round-trips (server not wedged by sync)
[PASS] meter broadcasts still flow
[PASS] server logged no traceback

sync-1 leader checks passed
```

The last three are regression: the ping loop shares `server.py`/`osc_bridge.py`
with every other dashboard path, so the verify confirms a param still
round-trips and meters still flow with sync running, and the server logs no
traceback.

## Caveat for the next session

The three **Playwright** dashboard suites (meters, facilitator, patch-mgmt)
were **not** re-run — this session's box has no chromium installed. The changes
are server-side only and additive (new ws message type `sync`, new runtime
field, new OSC verbs); no `static/` JS or HTML changed, so DOM behaviour is
unchanged by construction, and the ws-level regression above covers the shared
server. If a full browser regression is wanted it is one command per CLAUDE.md
(`playwright install chromium --only-shell`, then run each `verify_*.py`).

## For the next stitches

- `sync-2-helper-cue`: the node side in `python/helper.py` — answer `/sync/ping`
  with a pong, **slew** the working offset toward each pushed
  `/<id>/sync/offset`, convert `/cue <cueId> <sharedTimeNs>` to a local
  monotonic deadline (`deadline = shared + offset`), fire the bare
  `/cue <cueId>` to PD on 7770. Keep the offset sign consistent with here.
- `sync-3-jitter-harness`: honest measurement (GPIO/click recorded together);
  simfleet's `fire_mono` logging is the software analogue.
- The dashboard UI does not yet *display* the per-device offset/RTT (the data is
  on the wire and in ws `sync`); a small facilitator/tech surface for it is a
  natural follow-up but not required by this stitch.
