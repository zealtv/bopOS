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

## The gate is cleared — do not re-open it

This stitch used to carry a design question: preserve the facilitator's
divergent metrics, or collapse them? **Bob ruled on 2026-07-30: collapse.**

> *"let's let facilitator collapse — we will restyle remote for iPad as a
> standalone pass."*

So the facilitator's copy dies with no attempt to preserve its values, and the
deliberate touch restyle is `feature-backlog/49-remote-ipad-restyle`. Do not
reopen this as a proposal, and do not hand-carry 38px/11px/9px forward on the
grounds that a tablet needs them — that is exactly the rule-by-rule defence the
ruling replaces.

Note honestly in `decisions.md` that touch ergonomics regress in the interim:
the collapse lands on `--row-h`, which `@media (pointer:coarse)` already resolves
to 34px in `control-panel.css` (a file both documents load), so touch support
survives but the bespoke tuning does not. Thread `49` owns restoring it.

## Work

- Delete `facilitator.css:91-107` and `style.css:335-342`.
- Take the payoff `05c` declined: one `css/param-generator.css`, anchored on
  `.live-param-gen`, holding the whole drawer — base layer and overrides
  together. `value-box.css` is the precedent and the only component stylesheet
  in the app today.
- Load it from **both** `index.html` and `facilitator.html`; they have different
  base stylesheets, which is why `value-box.css` exists at all.
- With one base layer instead of two competing ones, the specificity doubling
  `05c` had to preserve (`.live-param-gen.live-param-gen`) may no longer be
  load-bearing. Check before simplifying it, and only simplify if the
  cascade probe still reports zero change — the doubling is cheap and being
  wrong here is not.
- Kill only the drawer's share. The rest of `facilitator.css`'s duplication dies
  component by component as `06`, `07` and `09` reach it; that is the thread's
  ratified approach ("each component stitch integrates into every consumer"),
  not a separate cleanup.

## Verification

`cascade_probe.py` from `.loom/tied/05c-drawer-component-ownership/` is the
harness — it locates the repo by marker, so it runs from `tied/`. Two extensions
are needed here that `05c` did not need:

- It currently loads `style.css`; parameterize the base stylesheet so the
  **facilitator** document's cascade is measured too. `05c` only ever proved the
  dashboard's.
- A `pointer:coarse` / tablet viewport run, since that is the cascade path the
  collapse actually changes.

Expect **non-zero** diffs this time, in the facilitator at touch sizes. That is
the ruling landing, not a regression — record the measured before/after values in
`decisions.md` so thread `49` starts from numbers rather than from guesses about
what it lost.
