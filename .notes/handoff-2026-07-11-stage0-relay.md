# Handoff — 2026-07-11 (Stage 0 relay)

`audition-1a-relay-launcher` is tied. `tools/audition.py` now owns one LAN
command socket, represents N deterministic virtual nodes, emits contract
heartbeats, selector-matches `/p/*` and `/os/master`, and forwards the stripped
engine surface to distinct local ports. Its verifier covers exclusive socket
ownership, selector isolation, PD startup values, partial-launch cleanup, and
owned process-group escalation. Commits: `8f22c00`, `91a1a7c`.

Stage 0 remains open through `audition-1b-pd-mac-gate.waiting`. Bob should make
the PD edit **now that the relay contract is tied**: consume startup
`BOPOS_ENGINE_PORT <port>` and feed a selector-free local engine inlet carrying
the rewrite-wave `/p/*`, `/os/master`, `/pt`, `/cue`, and `/id` routes. The
exact edit and Mac acceptance run are in that waiting stitch and
`.notes/pd-edits-for-bob.md` item A7. Agents must not edit `.pd` files.

Bob also requested a SuperCollider audition rig with agent-built test patches.
Next session, add a bounded child under `audition-1-stage0-launcher` for:

- a small SC test patch/manifest using `BOPOS_ENGINE_PORT` and
  `BOPOS_AUDITION_ID`;
- per-instance SC language/server ports and CoreAudio stereo mixing;
- integration with `tools/audition.py` for three instances; and
- audible plus dashboard verification.

SuperCollider is not installed on this Mac, so runtime work will require an
approved installation. JACK is also absent; prefer SC/CoreAudio first. Do not
claim the PD gate complete until three real PD instances are audibly verified.

## Deferred architecture question

The full design-session input is now preserved in:

- `.lore/items/2026-07-11-pd-engine-boundary-brain-dump/` — Bob's verbatim
  patching-session observations; and
- `.notes/pd-engine-boundary-design-brief.md` — a revisable question set for
  the future higher-capability design session.

The current PD OS layer receives a LAN command, strips its framework routing,
then forwards selected lifecycle/provisioning verbs back to helper on localhost
7770. This works as a compatibility bridge, but it is a boundary smell: helper
already owns node administration and ideally should receive the LAN command
directly, with PD only consuming its local engine surface. Include this in the
future higher-capability design discussion together with identity and launch
context ownership; do not broaden the current PD rewrite to solve it ad hoc.
