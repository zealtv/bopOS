# 49-remote-ipad-restyle

Restyle the Remote view for iPad as a deliberate standalone pass.

Bob, 2026-07-30: *"let's let facilitator collapse — we will restyle remote for
iPad as a standalone pass."*

## What the ruling settles

`05e-drawer-base-layer-consolidation` had opened a question: are the
facilitator's hardcoded metrics pre-token leftovers, or a ratified tablet
divergence to preserve? **Answer: leftovers.** The facilitator's duplicated
rules collapse onto the shared component layer as each component stitch reaches
them. Nobody protects `facilitator.css` values on the way through, and no stitch
needs to ask this question again.

The touch surface is not being abandoned — it is being **deferred deliberately**,
so that it is designed once, whole, against the finished component set, rather
than defended rule-by-rule inside seven refactors.

## Why the interim state is acceptable

`--row-h` already resolves to 34px under `@media (pointer:coarse)`, and that
token layer is in `control-panel.css`, which **both** documents load. So the
collapse does not drop to desktop metrics on a touch device; it drops to the
shared coarse-pointer override. The loss is the bespoke tuning
(`min-height:44px` where the token gives 34px, `font-size:14px` where the
component gives 12px), not touch support altogether.

That is a real regression in touch ergonomics until this stitch runs. **Say so
to Bob before a live show** if one is scheduled while this is outstanding — 44px
to 34px is a smaller tap target on a surface someone uses standing up, in the
dark, mid-performance.

## Scope when it runs

`facilitator.css` is 126 lines and the divergence is pervasive, not localized:
8 × `min-height:44px`, 10 × `font-size:14px`, plus its own radii and paddings.
Expect most of the file to be gone by the time this starts — killed component by
component — and this stitch to be about what *replaces* it:

- One deliberate `@media (pointer:coarse)` metric override layer, per the
  ratified rule that mobile divergence is a metric override and not a parallel
  layout.
- Tap-target sizing decided once, as a number with a reason, rather than
  inherited from whichever 2026 stitch last touched a rule.
- Real iPad verification. Playwright's `pointer:coarse` emulation is not a
  finger; this needs the actual device, so it is hardware-gated.

Read `.loom/tied/05c-drawer-component-ownership/decisions.md` for how the two
base layers were found, and `05e` for the drawer's share of the collapse.
