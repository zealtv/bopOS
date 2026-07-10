# spatial-0b-redesign-review

**Waiting on Bob.** The 2026-07-09 `spatial-0` engine used the wrong model
(dashboard-computed per-device gain into the volume slider, single point) and
was reverted 2026-07-10. The replacement — node-side decomposition of broadcast
points into a flexible patch parameter, arbitrary point count — is drafted.

This stitch is the **review gate before implementation**:

- [ ] Bob reads the design draft: `.lore/items/2026-07-10-spatial-points-node-side/
      content/draft.md` (context/plan: `.notes/spatial-redesign-plan-2026-07-10.md`).
- [ ] **Decide the session format for S1** (point wire + node decomposition):
      a `council-design-session` (multi-model, Bob as judge) or an interactive
      co-design with Bob. The draft is the input either way.
- [ ] Settle the draft's open questions (§8): wire shape (`/pt` per-point vs
      per-frame), PD receiver convention (Bob's domain), manifest declaration
      y/n, raw-distance now/later.
- [ ] Output: ratified proposal + **contract §4 amendment** (node-side `/pt`
      becomes primary; overturns the Stage-A-first framing). Then spawn the
      implementation stitch(es): `helper.py` + `simfleet` decomposition + the
      wire; re-scope `spatial-1` (→ author/move points) and keep `spatial-2`
      (synced sample start).

Deferred to a later session **S2** (addressing/identity — device vs element,
split-channel): don't fold it into S1; noted in the draft §7.

Salvage: the falloff curves from the reverted `dashboard/spatial.py`
(recoverable at commit `0ce8821` / `.loom/tied/spatial-0-engine/`) move
node-side in the implementation.
