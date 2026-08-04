# 1-theme-control-height

> the theme button can be a bit smaller so it has some vertical padding when
> the view is wide — Bob, 2026-08-02

## Measured starting state (2026-08-02, real app at 1440 × 900)

The control is the header's theme `<select>`, not a button:
`dashboard/static/index.html` line 6, styled by
`dashboard/static/css/style.css:100`.

```
header            top 0   height 40   (--header-h: 40px)
#theme-select     top 0   height 40   min-height: 40px
#execution-target top 1   height 38   min-height: 38px
.app-brand        top 10  height 20
```

So the select is **flush with both header edges — zero vertical padding**,
which is exactly the report. The execution-mode group beside it has 1px each
side, which is barely better and worth looking at while you are here (Bob named
only the theme control; do not restyle the mode group beyond whatever falls out
of a shared token).

## The cause is a stale bespoke number

`--header-h: 40px` and `.theme-control select { min-height: 40px }` are the
same literal, arrived at separately. `02-token-promotion` retired `--chrome-*`
and moved app chrome onto `--row-h`/`--gap`/`--pad-control`, but this rule kept
its own 40px, as did `#mute-all` beside it — and `#mute-all` has since left the
header entirely for the Monitor dock's Globals panel
(`03-global-controls-monitor`), so the 40px it was matching is no longer even
there to match.

## Scope

Bring the theme control onto the one metric layer so it derives its height
rather than restating the header's. `--row-h` is 24px desktop / 34px coarse
pointer; the header has room for either with padding to spare at 40px.

Check the narrow breakpoints while you are in the file —
`style.css:101-115` re-lays the header at 1049px and 700px, and at 700px the
theme label is visually hidden so the select stands alone. Bob's report is
about the **wide** view; do not make the narrow one worse.

## Verify

A browser measurement, not an assertion of the literal. The rule to pin is
**the header is taller than its tallest control**, which is
`09-patches-deploy-row`'s gotcha in its correct form:

> "the controls share a `top`" is the wrong test — shorter buttons centred
> against taller selects have different tops on the same line. Measure the row
> against its tallest control instead.

`tests/verify_ground_and_card.py` already walks real surfaces at real sizes and
is the nearest living journey; extend it or the nearest header check rather
than adding a new file for one number. Fail it against the current tree first
(`40 vs 40`) so it is a guard and not a description.
