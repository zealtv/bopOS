# 05e-drawer-base-layer-consolidation

Found while working `05c`. The generator drawer's styles live in **three**
files, and two of them are duplicated base layers:

- `style.css:335-342` — 8 `.live-param-gen` rules, token-valued.
- `facilitator.css:91-107` — 12 `.live-param-gen` rules, the same properties
  with hardcoded tablet metrics (`min-height:38px`, `padding:11px`,
  `border-radius:9px`, `gap:7px`).
- `control-panel.css` §8/§13 — the overrides on top, re-anchored to
  `.live-param-gen` by `05c`.

`05c` deliberately left these alone and said why: they are **already** anchored
on the component, so they violate DRY rather than component ownership, and
`05d`'s guard will correctly pass on them. They are a distinct defect, not
unfinished business from `05c`.

The reason they cannot simply be merged is that the two base layers genuinely
differ, and the difference is geometry — which `05c`'s instructions excluded.

The question to settle first:

- CLAUDE.md ratifies that **mobile divergence is a metric override**
  (`@media (pointer:coarse)`), not a parallel layout, and the standalone
  facilitator "keeps its tablet-first constraints." Those two statements pull in
  different directions for this file. If the facilitator's 38px/11px/9px are
  pre-token leftovers, they become a `(pointer:coarse)` override of `--row-h`
  and friends and one base layer serves both documents. If they are a ratified
  tablet divergence, they stay — but then they belong in a named override block
  rather than a silent copy of the same eight rules.
- `--row-h` already resolves to 34px under `(pointer:coarse)`, so most of the
  divergence may already be expressible in tokens both documents load.

**This likely needs Bob**, because "the Remote view's controls are deliberately
bigger" is a design position, not a refactor. Produce the proposal, mark
`.waiting` if the answer is not already implied by the tokens, and do not
unify by guesswork — a silently shrunk iPad control surface is a live-performance
regression.

If the answer is "tokens," the payoff is the component stylesheet `05c`
declined: one `css/param-generator.css` anchored on `.live-param-gen`, loaded by
both documents, holding the whole drawer.

Verification must include the `cascade_probe.py` harness from `05c` (it locates
the repo by marker, so it runs from `tied/`) extended to the facilitator's
stylesheet, plus the tablet/touch viewport that only the Remote view uses.
