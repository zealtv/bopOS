# Decision list — questions the co-design session must answer

*Fable brainstorm, 2026-07-15. The distilled agenda: if the `scene-sequencing`
design session answers these, everything in this folder becomes implementable.
Ordered roughly by how much they gate.*

## Shape of the system

1. **Ratify the identity:** sequencer = dashboard tab + separable backend
   module, shows as text files. (Alternative on record: standalone app.
   §02 argues tab; the fallback stays open via the module boundary.)
2. **Ratify polymorphic clip types** sharing one grid chrome, all
   round-tripping to text — vs one universal language for every clip.
   This decision shapes the language work more than any syntax choice.
3. **First slice:** Rung 1 (cue clips + grid chrome, no contract change)
   before any language design — yes/no. (§05 argues yes: it produces the
   artifact the language session should react to.)

## Contract questions (each needs Bob's ratification, all additive)

4. **`/field` term** (§03A): shape set (linear / radial / spin / noise /
   const enough?), delivery like `/pt` (`/field <id> <element> <v>` shaped
   scalars, patch maps meaning — the seam-pure option) vs direct param
   binding, shared-clock phase encoding, silence=hold + slow re-assert,
   `/field/clear`.
5. **Ramp decomposition home** (§05 Rung 2): patch-side convention with a
   starter-kit helper (`v t` pairs, seam-pure) vs bopos.py ramping `/p`
   values framework-side. Also: does a ramp *segment stream* at low rate
   count as "streaming" under the transport law, or is pre-scheduled ramp
   delivery exempt because it's bounded and full-state?
6. **Scatter primitive** (§04.5): node-side seeded coin-flip on broadcast
   cues — ratify as a cue argument, a separate term, or keep dashboard-side
   (unicast picks) until fleets get big?
7. **Cue args in general:** `/cue <id>` today carries no payload. Pattern
   clips and cue echoes (§06) both eventually want args (velocity-like
   values, repeat figures). Additive now or explicitly later?
8. **Scheduled param writes:** is there ever a `/p`-with-deadline (cue-plane
   timestamping for param sets), or do cues remain the only time-critical
   citizens and params stay best-effort? (v1 position in §02: cues only;
   ramps absorb most needs.)

## Semantics

9. **Transport/tempo model:** optional per-show tempo, per-clip choice of
   musical vs clock time (§02) — confirm, and decide where tempo lives
   (show file? scene? live control?).
10. **Takeover semantics:** one playing clip per track, last-writer-wins per
    address, stop-leaves-values (§02). Confirm as v1 law; park crossfades.
11. **Lookahead horizon & cancellation:** short horizon v1 (≤ launch
    quantum) vs `/cue/cancel` term (§02). Confirm short-horizon.
12. **Follow-action vocabulary:** Ableton's set (next / previous / random /
    other / stop, after n plays) — enough? Add scene-level follow actions
    now or at v1.5 (§06)?

## Language (the co-design proper — after the above)

13. Which seed grows into which clip type: `.bopseq` → ramp/timeline,
    intermals → pattern (§04) — and what shared core (targets, time words,
    randomness) both inherit.
14. The agent-writability acceptance test, kept literal: an LLM writes a
    valid scene from the docs alone; `lint` exists from day one.

## Explicitly parked (state it and move on)

- Scene/parameter crossfading and mixing.
- Live video sampling as a default path (gated experiment only).
- MIDI grid controllers, sensor-conditioned follow actions, auxiliary-rig
  integration ("everything is a seat" test).
- Field-fitting of live textures (§03B.2).
