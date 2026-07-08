# sensor-data-view

**Split 2026-07-08 from dashboard-4-patch-mgmt — blocked on Pi-side work.**

The phase-4 sensor item: live per-device I/O values in the dashboard. Today
port 6662 is **localhost-only** (PD ↔ `python/io/main.py` reply path, contract
§4 port map) — nothing surfaces I/O values to the fleet/dashboard.

Blocker / prerequisite (design decision, likely Bob's):
- Contract §11 says framework-owned bus I/O is the `/io/*` plane and
  engine-native input surfaces as `/p/*`. There is no fleet-facing *stream* of
  live I/O readings. Deciding how sensor values reach the dashboard is a
  contract question:
  - option A: a throttled `/io/report`/`/io/value` unicast to 5550 on request
    or subscription (framework plane), or
  - option B: the patch republishes the values it cares about as `/p/*` and the
    dashboard already renders those — no new framework surface.
- Either way it needs a Pi-side emitter and a rate/precision decision (PD
  32-bit float constraint; no per-frame framework traffic on the engine socket,
  §12).

Do first: write a short proposal (A vs B, rate, which values), mark `.waiting`
for Bob — this is engine-strategy/contract-adjacent. Build only after a ruling.
Coordinate with `osc-schema-contract` (now tied) and `audio-input`.

---
**2026-07-08: proposal written (`proposal.md` in this stitch), waiting on Bob.**
Recommends Option A (patch/helper republish values as read-only `/p/*`, dashboard
renders meters) over Option B (new `/io/report` stream). Note the shared
`role` field question with the facilitator proposal. Build after Bob rules.

---
**2026-07-08: RATIFIED by Bob** — "re sensor data view / role: meter / is
consistent with the above." Option A with the `role: "meter"` spelling
(matching the facilitator view's `role: "volume"` — one `role` field, two
values so far). Build now.
