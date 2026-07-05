# osc-schema-contract

**Goal:** tidy the OSC schema and write the contract down as a first-class spec, so any
engine or controller can sit on either end of bopOS.

Context: `.notes/architecture-review-2026-07-05.md` §4, §7. **Overlaps kite-choir-brains
loom thread `bopos-uptodate/osc-contract-pd-agnostic`** — coordinate/absorb, don't
duplicate. That thread stays spool-scoped; the generic work lands here.

**Do this ahead of dashboard build** — schema decisions steer the dashboard design
(Bob, round 2). Specifically rethink, don't just document:

- **Framework vs patch namespaces:** `/gain` `/gain2` `/backing` are *patch-specific*
  targets, not framework — the contract needs a clean split (e.g. `/os/*` framework,
  `/p/*` or patch-declared parameter namespace) so the dashboard can discover a patch's
  parameters instead of hardcoding three sliders.
- **`/echo` is an OSC echo-back hack** — either move it into helper.py as a proper
  liveness/latency probe, or remove it in favour of deliberate discoverability/debug
  design (e.g. `/os/ping`, parameter listing, verbose-mode reporting).
- **The ports smell** (quantity, arbitrary numbers, overall protocol design). Consider:
  fewer sockets, coherent numbering, or single-port-with-namespaces on each side; weigh
  against migration cost for deployed fleets.

Checklist:
- [ ] `docs/OSC-CONTRACT.md`: full port map, namespaces, message shapes, and the
      constraints (PD 32-bit float precision; longs-as-strings rule)
- [ ] Framework/patch namespace split + patch parameter discoverability (above)
- [ ] `/echo` resolution (above); port-map rationalisation decision recorded
- [ ] Namespace rename `/helper/*` → `/os/*` (keep `/helper` aliased for one transition
      release; plantsOS README already planned this)
- [ ] **Move the heartbeat from PD into helper.py** and give it identity:
      `/hb <mac> <id> <version> [rssi]` — engine death ≠ device death; lands the
      kite-choir RSSI-first-class decision (switchable via `bopos.config`)
- [ ] Generalise the patch entrypoint: patch declares how it starts (its own `start.sh` /
      manifest) instead of bopOS assuming `pd main.pd`; PD remains the reference engine
- [ ] Reserve/sketch namespaces for the new features: `/sync/*`, `/cue`, `/point`
      (see `clock-sync`, `spatial-audio`)
- [ ] Fix `stop.sh` pkill-everything (targeted process management; it currently kills any
      python and is why `/patch` restart is fragile)
- [ ] OSC-driven persistence key/value store (plantsOS TODO: PD sends key+values,
      Python persists, returns on load)

Done when: the contract doc exists, heartbeats carry identity from Python, and a device
with PD stopped still reports itself alive.
