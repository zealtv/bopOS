# sync-1-leader

Leader side: the dashboard backend broadcasts pings and estimates per-device
offsets. Mechanism in `../instructions.md` (HB-style); wire shape from
`sync-0-wire-shape` (do that first).

- [ ] Pinger in `dashboard/server.py` (or a module it owns): broadcast
      `/sync/ping` at 500±100 ms (randomised — avoid lockstep bursts).
- [ ] On pong: `oneWay = roundTrip/2`, `offset = (deviceTime + oneWay) - leaderNow`;
      smooth over many rounds (HB uses a rolling window; median or trimmed mean —
      record the choice). Discard outlier RTTs.
- [ ] **Implementer's call (record in this file): offset math leader-side vs
      device-side.** Parent instructions leave it open; pick one, document why,
      and keep sync-2 consistent with it.
- [ ] Surface per-device offset/RTT/last-sync in the dashboard device state
      (runtime-only, like meters — never persisted or pushed back).
- [ ] verify_*.py against simfleet's fake offsets: estimator converges to the
      configured offset within tolerance despite injected jitter.

No PD involvement anywhere in this thread — helper.py owns the device side.
