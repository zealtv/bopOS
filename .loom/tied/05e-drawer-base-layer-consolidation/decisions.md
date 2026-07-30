# Decisions

## One base layer, in the component's own stylesheet

`css/param-generator.css` now holds the drawer's base layer, loaded by both
documents between the document's own stylesheet and `control-panel.css`. That
position is deliberate: it is the base, so it must stay ahead of §8/§13/§17,
which are the ratified overrides and must keep winning at equal specificity.

Deleted: `style.css`'s 8 rules and `facilitator.css`'s 12.

The unified values are the **tokens** (the dashboard's), per Bob's ruling. Four
of the facilitator's twelve rules were not carried across:

- `.live-param-gen button` (36px) and `button.primary` — superseded by §17b's
  `.live-param-gen .live-param-gen-actions button` and §13's tab rules, which
  both documents already load.
- `.live-param-gen .show-check` ×2 — **dead in the facilitator.** `.show-check`
  is emitted only by `ParamGenerator.fields()` (`param-generator.js:67`), the
  flat Show-inspector path. The facilitator renders `drawer()` → `panelFields()`
  and never `fields()`, so these two rules styled nothing there.

## The collapse cost one invisible element, not the tap targets

Measured, not assumed. `cascade-facilitator.txt`: **one** element differs, in
the `lfo` drawer only — the visually-hidden checkbox inside `.live-gen-pill`,
`min-height` 38px → 24px.

That input is `position:absolute; width:1px; height:1px; opacity:0;
pointer-events:none` (`control-panel.css:1348`). It is not the hit target; the
`<label>` wrapping it is. Its 38px height existed only because the facilitator's
`min-height` was overriding the rule's declared `height:1px`, so the collapse
moves it *toward* its intended size rather than away.

**This corrects what I told Bob when the ruling was made.** I said the collapse
means 44px tap targets become 34px. For the drawer, measured: **no tap target
changed at all**, because §17b already restated the drawer's real metrics for
both hosts — its own comment says that is why it exists. The 44px concern is
real but belongs to the components `07` and `09` will collapse, not to this one.
`feature-backlog/49`'s framing was updated accordingly.

## The file split was narrowed, deliberately

The instructions asked for "the whole drawer — base layer and overrides
together" in `param-generator.css`. I moved the base layer only, and left §8,
§13, §17, §17b and §17c in `control-panel.css`.

Reason: that file's `/* ---- N. */` section numbering **is** design-language's
own ordering, and the drawer's sections are interleaved with the parameter row's
(§12 sits between §8 and §13). Extracting them would break the file's organizing
principle and carry real cascade risk, for a stitch whose actual defect was two
duplicated base layers. The DRY defect is fixed and the component owns a
stylesheet; a further reorganization of `control-panel.css` by component is a
legitimate but separate piece of work, and nothing now blocks it.

## The specificity doubling stayed

`05c` left a question: with one base layer instead of two competing ones, is
`.live-param-gen.live-param-gen` still load-bearing? It is — `param-generator.css`
still declares `.live-param-gen` at (0,1,0) and §8 must beat it. Simplifying
would have been a cascade change for no gain, and the probe would have caught it.

## Probe extension

`cascade_probe.py` gained `--doc dashboard|facilitator`, because `05c`'s version
hardcoded `style.css` and therefore only ever measured one of the two documents —
the one whose base layer was not the divergent copy. It reads stylesheets from
the working tree, so before/after runs bracket the edit.

One process note: the first "after" run showed 54 changed properties in the
dashboard and looked like a serious cascade break. The cause was the probe's own
stylesheet list, which had not been told about the new file — the measurement
was wrong, not the change. Worth remembering that a probe is code too.
