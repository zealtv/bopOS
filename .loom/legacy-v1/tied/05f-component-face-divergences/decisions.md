# Decisions

All ten allowlisted rules are **discharged**, not re-scoped. `ALLOWED` in
`tests/test_css_component_ownership.py` is now empty and green.

## 1. PrecisionField's face moved onto the component

Deleted: `style.css`'s three `output.precise-output` rules and its
`.params .precise-input`; `facilitator.css`'s `.live-param .precise-input`;
`control-panel.css`'s panel-scoped focus/border block and its
`.live-param > .precise-input` sizing block. `value-box.css` now carries the
readout's `cursor`, hover outline and focus ring.

Two of the four "widths" were **already dead**: `.params .precise-input`'s 70px
and `facilitator.css`'s 72px both tie `value-box.css` on specificity and lose on
source order, so the patch editor and Remote view were already rendering 58px.
Measured, not assumed — `precision-dashboard.txt` reports both as `unchanged`.
The duplication was real; two of its three divergent widths were fiction.

`control-panel.css`'s row sizing (`width:100%`, `flex:none`, `box-sizing`,
`height`) was genuinely live but redundant: the row's first grid column **is**
58px (§12, `grid-template-columns:58px minmax(0,1fr) 18px`) and the component's
width is 58px, so `width:100%` restated the component's face from the surface.
`flex:none` was inert in a grid. Only `padding:0 4px` → `0 5px` actually
changes, inside a fixed-width box.

## 2. Cyan focus ring → purple, app-wide

`style.css` gave every precision readout `outline:2px solid var(--accent-cyan)`.
Cyan is reserved for modulation (§2, §5, and `05b` widening it to "something is
driving this"); a static readout is not modulated. `control-panel.css` had
already corrected this **inside the panel only** — the right fix at the wrong
scope, which is this thread's recurring shape. Purple now, everywhere, from the
component. The patch editor and Show inspector readouts change colour on focus;
that is the intended correction.

## 3. The ∿ glyph: §5 wins (Bob, 2026-07-30)

Bob ruled the circle holds everywhere and the Show inspector adopts it.

Deleting the override was **not sufficient**, and the naive version of this fix
would have shipped an unstyled glyph: §6's circle was itself scoped to
`.live-card`/`.device-control`, so the Show inspector would have fallen back to a
plain button. "Always an 18px circle" cannot be delivered by a rule that names
two of the three surfaces drawing one — that scoping is *why* the divergence was
possible. §6 is re-anchored on `.live-param-mod.live-param-mod`, same doubling
idiom as `value-box.css` and §8.

### The ruling exposed a shipped defect in §5's own surface

The new assertion in `verify_show_generator_drawer.py` failed first time at
`height: 24px`. Cause: §6 set `height:18px` but not `min-height`, and the app's
generic `button` rule sets `min-height:var(--row-h)` (24px), which beats a plain
`height`. **So §5's "circle" has been an 18×24 oval in the control panel for as
long as it has shipped.** The Show inspector's deleted override stated
`min-height:18px`, so the diverging surface was the geometrically correct one
while being wrong on ink. §6 now states `min-width`/`min-height` too.

Worth noting how this was caught: by asserting the ratified rule in the surface
where it had been untrue, rather than in the surface that owns it. A guard
pointed at the known-good host would have passed.

## Probe limitation, stated

`precision_probe.py`'s host templates are a bare `<div class="live-param">`, not
the real grid, so its `width` column reads 1280px before and 58px after. That
delta is a **probe artifact**: in the app the cell is 58px, so `width:100%` and
`width:58px` compute identically. The trustworthy columns are ink, radius, font,
padding and cursor; for width the authority is
`verify_precision_param_input.py` and `verify_control_tab.py`, both of which
drive the real panel and pass.
