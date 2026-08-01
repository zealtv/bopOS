# Ratification — Bob, 2026-07-13 (verbatim feedback + rulings)

Bob's feedback on `proposal.md`, verbatim:

> here's my feedback: 3 - i don't foresee a situation where we need a half
> simulated and half real fleet.
>
> when simulation is "on" that can be a separate state from performance
> entirely.  All seats are filled with sims.  Simpler.
>
> We may need to limit the number of sims at some point.  that can be
> deferred for now.
>
> 4 - ok
>
> 5 -ok
>
> 7 - there are no old schemas. hard break.
>
> Q1 seat is good
>
> Q2 audition rig only is good
>
> Q3 simulate everything. simple is prefered. two distinct modes.
>
> Q4 on recently seen is good
>
> Q5 auto rebind is good
>
> Q6 yes - useful

## Rulings as applied

- **Ratified as proposed:** the seats/devices split, binding via existing
  `/os/assign`, **"seat"** as the noun (Q1), Simulate = audible audition rig
  only, simfleet stays a CLI dev tool (Q2), forget + bulk-forget with
  confirm gate only when recently seen (Q4), auto-rebind on venue load when
  a remembered uid heartbeats (Q5), `hostname` joins `/os/report` as the
  additive wire change (Q6).
- **Amendment — simulation is a mode, not a fill-in (Q3 + §3):** no
  half-sim/half-real fleets. **Simulation ON is a distinct state from
  performance entirely: every seat is filled with a sim instance**,
  regardless of any real devices. Two distinct modes, simple. Design
  consequence to honour in implementation: entering simulate while real
  assigned devices are live would collide seat ids on the broadcast plane —
  the mode switch should warn/expect the performance fleet to be inactive;
  no dual-driving logic is to be built.
- **Deferred by Bob:** a cap on the number of sim instances (revisit when a
  big seat count makes the laptop struggle).
- **Amendment — no migration (§7): hard break.** There are no old schemas
  to honour; the new `installation.json` shape simply replaces the old one
  (existing state files are discarded/recreated, consistent with the
  patch-asset-sync hard-break posture).

Consequences executed at tie time: `d8-1..3` children created under the
`dashboard` thread with the rulings folded in (implementation deferred by
Bob alongside dist-1..4); hostname-in-report folded into
`dist-1-contract-amendment` + `dist-2-node-side` so the node-side change
lands once; coordination notes updated in ui-0/ui-2.

## Addendum — Bob, 2026-07-13 (same day, post-ratification)

On the seat id collision (sim instances and real devices sharing ids on the
broadcast plane): Bob asked whether piping OSC to localhost rather than
broadcast fixes it — yes, adopted as the mechanism: **the mode is the send
target**. Performance mode sends to LAN broadcast; sim mode sends unicast to
`127.0.0.1:6660` (relay is sole binder). Assign-replay to real devices
pauses in sim mode. This supersedes the earlier "warn on toggle" mitigation;
recorded in `d8-2-simulate-toggle`.
