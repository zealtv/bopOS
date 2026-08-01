# seam-1-contract-amendment

**Ratify gate — waiting on Bob.** Apply the seam-council ruling to
`docs/OSC-CONTRACT.md`. The exact replacement text is drafted in
**`contract-amendment-draft.md`** in this stitch dir; Bob reviews that draft,
amends spellings as he likes (receiver names are his), then whoever holds this
stitch applies it verbatim and ties.

Authority: `../seam-0-council` (tied) — `judgment.md` as amended by
`ratification.md` (ratification wins). Bob's rulings already folded into the
draft: no backwards compat (patches rewrite in lockstep), master
unconditional, no `subscribes` field, one-instance-N-elements via internal
cloning, true-N position list (pos2 label retired), routed single receiver /
flat args, install-level facilitator command allowlist (default empty), mute
multi-board note.

- [x] Bob reviews `contract-amendment-draft.md` (flag any spelling changes)
      — reviewed 2026-07-11, **no spelling changes**; three follow-on notes
      routed per `bob-review-2026-07-11.md` in this dir
- [x] Apply the edits to `docs/OSC-CONTRACT.md`; bump the version line and
      add the provenance (seam council, `.loom/tied/.../seam-0-council`)
      — applied verbatim (v1.0 → v1.1) plus one flagged editorial
      reconciliation (§3 bare-`/gain` parenthetical vs Edit 8's lockstep
      ruling; see the review record)
- [x] Reconcile `README.md`'s port/plane blurb if it repeats amended text
      — checked: it doesn't repeat any amended text; no change
- [x] On tying, **un-wait the gated siblings** so autopilot can take them in
      numeric order: rename `seam-2..5`'s `.waiting` suffixes away (they are
      `.waiting` solely on this gate) — done
