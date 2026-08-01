# sync-1-leader

Leader side: the dashboard backend broadcasts pings and estimates per-device
offsets. Mechanism in `../instructions.md` (HB-style); wire shape from
`sync-0-wire-shape` (do that first).

- [x] Pinger `OSCBridge.sync_ping_loop()`: broadcasts `/sync/ping` at 500±100 ms.
- [x] `handle_pong()`: `oneWay = rtt/2`, `offset = (deviceTime + oneWay) −
      leaderNow`; smoothing = low-RTT-band median over a 16-sample window;
      RTT < 0 or > 200 ms discarded. Choice + rationale in `results.md`.
- [x] **Implementer's call: offset math leader-side** (only the leader sees the
      round trip; cues are broadcast so the node holds/applies its own offset).
      Settled in sync-0; sync-2 must stay consistent. Recorded in `results.md`.
- [x] Per-device `sync = {offset, rtt, min_rtt, samples, at}` surfaced runtime-only
      (`state.py`; excluded from `durable()` like `meters`, never pushed back),
      broadcast as a throttled `sync` ws message.
- [x] `verify_sync_leader.py` (browser-free ws): estimator converges to the
      configured skew within 10 ms despite 2 ms jitter; + regression checks.
      Results in `results.md`. NB: Playwright suites not re-run (no chromium
      here); changes are server-only/additive — see the caveat in `results.md`.

No PD involvement anywhere in this thread — helper.py owns the device side.
