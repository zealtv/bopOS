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

- [ ] Bob reviews `contract-amendment-draft.md` (flag any spelling changes)
- [ ] Apply the edits to `docs/OSC-CONTRACT.md`; bump the version line and
      add the provenance (seam council, `.loom/tied/.../seam-0-council`)
- [ ] Reconcile `README.md`'s port/plane blurb if it repeats amended text
- [ ] On tying, **un-wait the gated siblings** so autopilot can take them in
      numeric order: rename `seam-2..5`'s `.waiting` suffixes away (they are
      `.waiting` solely on this gate)
