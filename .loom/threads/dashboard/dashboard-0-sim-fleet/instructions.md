# dashboard-0-sim-fleet

**Do this before (or at the very start of) dashboard-1-core.** Build `tools/simfleet.py`:
a simulated bopOS fleet so dashboard, clock-sync, and scene work can be developed and
verified with zero hardware.

Spec:
- `python tools/simfleet.py --devices 5 [--drop 0.05] [--jitter-ms 30]`
- Each simulated device: fake MAC/ID (drawn from a `bopos.devices`-style file or
  generated), heartbeat + `/rpt`/`/id`/`/version`/`/aloha` on 5550 exactly as
  `bopos.osc.pd` + helper.py send them today (UDP broadcast, same payload shapes —
  read the real code, don't guess), and responds to 6660 commands (`/<id>/...`,
  `/all/...`): gain changes acknowledged in state, reboot = go silent then return,
  shutdown = go silent, update = delay then version bump.
- Optional realism flags: packet drop, latency jitter, a device that never answers —
  these are what make dashboard resilience code honest.
- Print a live one-line-per-device state table so a human can eyeball it.
- Plain Python 3 + python-osc, no other deps; runs on the laptop.

Contract-tracking rule: when any stitch adds or changes an OSC message (heartbeat
identity, `/sync/*`, `/cue`, samples namespace), extending simfleet is part of that
stitch's deliverable — the simulator must never drift from the contract.

**2026-07-07 note:** `docs/OSC-CONTRACT.md` v1.0 is ratified. Build simfleet against
*today's deployed wire protocol* (the shapes above — that's what real Pis speak until
the `osc-schema-contract` children land), but structure device state/handlers so
message shapes are cheap to swap: `hb-identity`, `assign-persistence`, and
`patch-manifest` will each migrate simfleet to the v1 messages (`/hb` with uid,
`/os/assign`, `/os/params`) as they land, per the tracking rule. Contract §13 lists
the transition aliases a mixed fleet needs.

Done when: dashboard-1-core development can run against `simfleet.py --devices 5` and
an unmodified real Pi appears in the same dashboard indistinguishably.
