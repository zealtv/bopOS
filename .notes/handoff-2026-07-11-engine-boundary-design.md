# Handoff — 2026-07-11 (engine-boundary design gate)

The Pure Data rewrite wave and real three-instance Mac gate are tied. That work
made the engine seam functional but exposed unresolved architecture questions
that Bob wants settled before extending the SuperCollider starter or audition
rig. The next and only recommended stitch is
`engine-boundary-council`; further Stage 0 work is blocked by
`audition-1c-engine-boundary-adoption.waiting`. The listener puck and musician
starter template also carry explicit design-adoption blockers so they cannot
freeze transitional port, meter, or namespace choices.

## Start here

```sh
./.loom/loom claim engine-boundary-council
```

Read its instructions and use the ai-kit council procedure. Do not begin by
designing from this handoff; write `ground-truth.md` from the required sources
first. The primary inputs are:

- `.notes/pd-engine-boundary-design-brief.md` — distilled questions;
- `.lore/items/2026-07-11-pd-engine-boundary-brain-dump/` — Bob's raw words;
- `docs/OSC-CONTRACT.md` and lore `2026-07-10-patch-seam-council`;
- tied PD/SC/audition evidence named in the stitch instructions; and
- the current PD, helper, IO, audition, and SC implementation.

## Session shape

Run five independent expert lenses: engine API, transport, operations,
creative tools, and simplification. Experts must not see each other's designs.
Use economical one-tier-down models for experts and the strongest available
model for the judge. The judge must verify claims, name the crux, rule on one
path, and provide a smallest implementation slice plus proposed Loom changes.

This is design-only. Write artifacts into the council stitch, tie it when the
record is complete, then claim `engine-boundary-ratification` and stop for Bob's
decision. Do not edit `.pd`, implementation code, or the ratified OSC contract
during the council.

## Current evidence and caveats

- Three PD/CoreAudio engines ran on distinct local ports; Bob heard element-0
  point noise on the left and identify notification on both channels.
- The audition relay required explicit mute and identify delivery in addition
  to patch params/master.
- Production fixed receivers still log expected bind collisions in audition.
- PD's legacy `255.255.255.255:5550` report path fails on this Mac with error
  49, so meter transport is not verified.
- Meter semantics, subscription/rate, element scope, IO traffic separation,
  `bopos-` namespace, identity/run context, helper naming, and PD-to-helper
  command forwarding are open design questions, not implementation TODOs yet.

No loom stitch is claimed at handoff. The obsolete `DASHBOARD.pd` and
`pd/bopos.gui.pd` files were removed in commit `aed34a1`.
