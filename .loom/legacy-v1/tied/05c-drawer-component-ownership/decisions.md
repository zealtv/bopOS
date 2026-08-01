# Decisions

## All 68 rules re-anchored; specificity preserved exactly

Every drawer rule in `control-panel.css` lost its
`:is(.live-card,.device-control,.show-inspector-section)` prefix and now anchors
on `.live-param-gen`, the root the drawer itself emits
(`param-generator.js:303`).

`:is(a,b,c)` weighs as its **most specific argument** — one class — so the old
prefix contributed exactly one class of specificity. Preserving that mattered
more than it first appeared (see the base-layer finding below), so:

| old | new | weight |
|---|---|---|
| `:is(hosts) .live-gen-num` | `.live-param-gen .live-gen-num` | (0,2,0) → (0,2,0) |
| `:is(hosts) .live-param-gen` | `.live-param-gen.live-param-gen` | (0,2,0) → (0,2,0) |
| `:is(hosts) .live-param-gen input` | `.live-param-gen.live-param-gen input` | (0,2,1) → (0,2,1) |

The doubling is the idiom `value-box.css` already uses, and a comment at §8 in
`control-panel.css` now says it is deliberate rather than a typo.

One boundary case the rewrite had to respect: `.live-param-gen-tabs`,
`-actions`, `-head` and `-error` merely share a *string* prefix with the root.
They are descendant classes and take the prefix form, not the doubled form. The
transform required an identifier boundary after the root class to tell them
apart.

## The file split was declined

The instructions preferred a `css/param-generator.css` "if it falls out
cleanly." It does not, and the reason is the finding below: the drawer's rules
live in **three** files, and lifting only `control-panel.css`'s share into a
component stylesheet would leave two base layers behind while implying the
component was now consolidated. Anchoring was the point; the split waits for the
base layers.

## Finding: the drawer has two duplicated base layers

`style.css:335-342` (8 rules) and `facilitator.css:91-107` (12 rules) each carry
a `.live-param-gen` base layer, and `control-panel.css`'s rules are the
overrides on top of them. This is why specificity was load-bearing: dropping to
a bare `.live-param-gen` would have let the base layers win in places.

This is a **different defect from the one this stitch fixes.** Those rules are
already anchored on the component — they violate DRY, not ownership. So `05d`'s
guard will (correctly) pass on them, and they are not silently in scope here.

They are also not trivially mergeable: the facilitator's values are hardcoded
tablet metrics (`min-height:38px`, `padding:11px`, `border-radius:9px`) where
`style.css` uses tokens. CLAUDE.md ratifies mobile divergence as a *metric
override*, not a parallel layout, which suggests those are pre-token leftovers
that should become `@media (pointer:coarse)` overrides — but deciding that is a
geometry change, and this stitch's instructions exclude geometry. Recorded as
`05e-drawer-base-layer-consolidation`.

## Finding for `05d`: a host can also be a component root

`.live-card` and `.device-control` are **both** — they host the drawer, and they
are the control panel component's own roots. The ~40 remaining
`.live-card`/`.device-control` rules in `control-panel.css` (buttons,
`.live-param`, `.live-param-mod`, focus rings) are legitimate: a component
styling itself.

So `05d` cannot classify a selector by "does it name `.live-card`." The
distinction is whether the selector's *subject* belongs to the same component as
its ancestor. A guard that treats `.live-card` as a host full stop will produce
~40 false positives and be switched off in a week.

## Verification approach: computed styles, not screenshots

The instructions suggested a screenshot pair. Computed-style dumps are strictly
better for a cascade question and much cheaper to read: `cascade_probe.py`
renders the drawer in all three real hosts × three generator kinds and diffs 27
properties on every element. A screenshot says "something moved"; this says
which element and which property.

It also renders the drawer in a **bare `<div>`** — the fourth mount point `06`
and `08` will create. That is where the old rules did nothing, so it documents
the latent bug as a measurement rather than a prediction: 36–46 elements per
kind change from unstyled sprawl (1280 × 673, `display:block`) to the correct
compact drawer (320 × 177, grid).
