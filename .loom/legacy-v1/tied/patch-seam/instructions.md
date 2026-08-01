# patch-seam

Re-draw the responsibility seam between bopOS and the patch (PD/SC/OF/other).

Instigated by the reverted `spatial-0` engine (2026-07-10): bopOS *enacted*
what it should merely have *offered*. Bob's framing (2026-07-10 session):
**bopOS provides a subscribable OSC surface; the patch enacts it; nothing is
enforced except safety (`/os/mute`)**. In scope: the provided-not-enforced
principle generally (master gain is the type case), per-patch promotion of
controls to the facilitator surface, and multi-element devices (1..N
positioned patch instances per device — design it so it lands additively,
stage what ships now).

Subsumes the S1 design session from
`spatial-audio/spatial-0b-redesign-review.waiting` (the node-side points
draft `.lore/items/2026-07-10-spatial-points-node-side/` is an input here).

**Council run and ratified 2026-07-10** — authority:
`.loom/tied/seam-0-council/` (`judgment.md` as amended by `ratification.md`).
Decomposition, in order:

1. `seam-1-contract-amendment` (`.waiting` on Bob reviewing the draft text in
   the stitch) — the gate; on tie it un-waits 2–5.
2. `seam-2-master-term` — `/all/os/master`, delete dashboard composition.
3. `seam-3-points-node-side` — the points implementation (helper + simfleet).
4. `seam-4-facilitator-promotion` — manifest flag + install verb allowlist.
5. `seam-5-sc-starter-kit` — SC templates (agent-buildable; PD twin is in
   `pd-edits-for-bob.waiting`).

Tie this goal when 1–5 are tied and `spatial-audio` has picked up its
re-scoped children.
