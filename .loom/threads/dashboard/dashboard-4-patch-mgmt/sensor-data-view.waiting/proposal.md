# Sensor-data view — design proposal (awaiting ratification)

Stitch: `dashboard/dashboard-4-patch-mgmt/sensor-data-view`. This is a
contract-adjacent / engine-strategy decision (CLAUDE.md gate), so: proposal
first, `.waiting` for Bob, build after a ruling.

## The problem

Phase 4 wants live per-device I/O values (knobs, sensors, RSSI) in the
dashboard. Today nothing carries them off-node: port 6662 is the
**localhost-only** PD ↔ `python/io/main.py` reply path (contract §4). The
`/io/*` plane (§11) is registry/config verbs, not a value stream.

## Two ways to surface values (pick one)

### Option A — patch republishes what it wants seen, as `/p/*`  ✅ recommended

The engine already owns its native input (§11: "If engine-side input must
reach the fleet or dashboard, it surfaces as `/p/*`"). A patch that wants a
sensor visible sends `/<id>/p/<name> <value>` outward on 5550 (the same
plane params already flow on). The dashboard **already renders `/p/*`** as
declared params — so a declared param with, say, `"readonly": true` shows as
a live meter instead of a slider. Framework I2C values (`sys_i2c`) that the
framework owns get republished by helper.py the same way.

- Pro: **almost no new surface.** One additive manifest flag
  (`readonly`/`role: "meter"`), a small helper republisher for framework
  buses, and a read-only render mode in the dashboard. No new port, no new
  contract verb, honours "engine owns native media IO."
- Pro: rate/precision fall under the existing `/p/*` rules — throttle at the
  source, 32-bit float ok for sensor ranges, uid/version stay strings (§12).
- Con: the patch author must opt each value in. That is arguably correct —
  only meaningful values should cross the wire on the constrained Pi Zero.

### Option B — a framework `/io/report` stream

Add `/<id>/os/io-subscribe <hz>` → helper unicasts `/io/value <name> <v> …`
to 5550 at a capped rate; dashboard subscribes per selected device.

- Pro: framework-general, no patch cooperation, covers pure-sensor nodes
  with no engine.
- Con: **new contract verbs + a new stream**, a subscription lifecycle to
  get right (unsubscribe on deselect/disconnect), and per-frame framework
  traffic risk on PD's single socket (§12 explicitly warns against this).
  Heavier for the 80% case.

## Recommendation

**Option A**, with B reserved for a later "headless sensor node" story if one
appears. Concretely, if A is ratified:

1. Manifest: optional `"readonly": true` (or `"role": "meter"`) on a param
   declaration. Validator + `docs/OSC-CONTRACT.md` §8 note.
2. helper.py: republish framework-owned I2C readings the node is configured
   to expose as `/<id>/p/<name>` at a throttled rate (config: which, how
   fast).
3. Dashboard: render read-only declared params as live meters (value + last
   update), no input control. Reuses the params render path.
4. simfleet: emit a couple of fake `/p/<meter>` values so the view is
   testable headless, like every other dashboard stitch.

## Questions for Bob

- A or B (or A-now-B-later)?
- The manifest flag spelling: `readonly` vs `role: "meter"` (params already
  use `group`; a `role` field would also serve the facilitator "volume"
  question — see `2026-07-08-facilitator-view-proposal` Q1, worth deciding
  together).
- Which framework values matter first (RSSI is already in the heartbeat;
  I2C knobs? a battery/temp?).
