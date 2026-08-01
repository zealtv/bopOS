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

**Measured correction (2026-07-30, after `05e` ran).** When this stitch was
written I said the collapse means 44px tap targets become 34px. For the first
component actually collapsed — the generator drawer — that was wrong: the
measured delta in the facilitator was **one hidden, `pointer-events:none`
checkbox's `min-height`**, and no tap target or visible control changed at all.
The reason is that `control-panel.css` §17b had already restated the drawer's
real metrics for both hosts, which is exactly why it exists.

So the tap-target concern is real but **unproven per component**, not a blanket
regression. Each collapse (`07`, `09`) should measure its own with
`cascade_probe.py --doc facilitator` and record the delta here, so this stitch
starts from a list of what actually got smaller rather than an assumption. Still
worth telling Bob before a live show if a collapse *does* shrink something
interactive — just don't claim it in advance of the measurement.

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

Read `.loom/legacy-v1/tied/05c-drawer-component-ownership/decisions.md` for how the two
base layers were found, and `05e` for the drawer's share of the collapse.

## Measured collapses so far

Each row is a component whose facilitator rules have already died, with what the
Remote view actually lost. This is the list the restyle should start from.

| component | stitch | measured delta on the touch surface |
|---|---|---|
| generator drawer | `05e` | **nothing visible.** One hidden `pointer-events:none` checkbox's `min-height`; `control-panel.css` §17b had already restated the drawer's metrics for both hosts. |
| target picker | `07` | **real shrink.** The All/Groups/Seat tabs were `min-height:44px`/`font-size:14px`; the replacement chips measure **34px tall** (`--row-h` under `pointer:coarse`), ~42px effective hit height with the component's `::after` pad, at 12px type. The seat `<select>` (`min-height:44px`, `min-width:140px`) became a row of **32px-wide** numeric Seat chips. Measured with `touch_probe.py` in that stitch, iPad-portrait emulation. |
| card chrome (the whole page shell) | `08/3-iframe-retirement` | **real shrink, four elements only.** `facilitator.css` carried the entire card face — it was never in a stylesheet `index.html` loads, which is why retiring the Control iframe forced the move. Measured on the live Remote page before/after (`remote_delta.py` in that stitch, 55 controls): 30 controls changed **width only** (the page gutter went 22px → 12px), and exactly **four** changed anything else. `.live-card` 18px/20px padding + 12px radius + 14px gap → 0 padding, 0 radius, 6px gap (the column is the card now, so the padding is the column's). `.live-card-head` 44px → 24px. The card name 19px → 12px. And the one genuine tap target: **`Send all` 88 × 44 → 54 × 24**. Every parameter row measured identical, `05e`'s reason again — §17b had already restated them. |

So the "44 becomes 34" worry is now **confirmed for two components and
disproven for one** — which is the point of measuring per collapse. Three
concrete jobs for this stitch fall out of the table: a Seat chip 32px wide is
the smallest tap target the Remote view has, a 34px chip in a scrolling roster
is the densest, and `Send all` at 54 × 24 is the smallest *button*. All three
want a number with a reason, not an inherited token.

The `08/3` row also changes this stitch's shape. Remote is now ONE
`ControlColumn` between a header and a footer, mounted at
`#control-column-host`, with `facilitator.css` down to page furniture. So the
restyle is no longer "rewrite a 126-line divergent stylesheet" — it is a
coarse-pointer override layer on `control-column.css` + `control-panel.css`
§18, which both documents already load, plus this page's own header/footer.
