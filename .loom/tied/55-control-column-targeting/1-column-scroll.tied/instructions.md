# 1-column-scroll

A Control column whose content is taller than the tab clips it, permanently and
silently. Nothing scrolls; the overflow is simply unreachable.

Claimable now. Independent of `2-multi-target-model` — a single card with a
long manifest overflows just the same, so this is a defect under either answer
to that design question.

## Measured (2026-08-02, real dashboard + simfleet, Chromium 1440 × 900)

Harness: `repro-columns.py` in the parent stitch.

```
#control-column-host   height 710   overflow-y: hidden
.control-column        height 710   max-height: 100%   scrollHeight 1448
.control-column-cards  height 1408  overflow-y: auto
                       clientHeight 1408 === scrollHeight 1408  →  NOT scrollable
```

Read that carefully: the **column** is clamped to 710 correctly, and the
**cards** element inside it has `overflow-y: auto` — but its client height is
its full content height, so `auto` has nothing to scroll. The 698px of overflow
escapes the column (which is `overflow: visible`) and is then clipped by the
host's `overflow-y: hidden`. No scrollbar appears anywhere, and there is no
visual cue that anything was cut.

Both configurations fail identically:

* three group targets × 8 params — cards 2 and 3 begin at y 731 and y 1192,
  against a host that ends at ~830;
* **one** group target × 40 params — cards 1408, viewport 900.

## Cause, and a fix candidate that measures clean

`css/control-column.css:47-58`:

```css
.control-column {
  max-height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, max-content);
  align-content: start;
}
```

The cards row is `minmax(0, max-content)`. With `align-content: start` there is
no compression step, so the track takes its **growth limit** — full content
height — regardless of the container's clamped `max-height`. The track never
shrinks, so the scrollport never becomes smaller than its content.

I probed three templates live on the overflowing tree:

| `grid-template-rows` | column | cards client | cards scroll | scrollable |
|---|---|---|---|---|
| `auto minmax(0, max-content)` *(shipped)* | 710 | 1408 | 1408 | **no** |
| `auto minmax(0, 1fr)` | 710 | **658** | 1408 | **yes** |
| `auto minmax(0, auto)` | 710 | 1408 | 1408 | no |

So `1fr` is the candidate. **Do not ship it on that measurement alone** — the
`max-content` choice was deliberate and its stated reason is the second host:

> `minmax(0, max-content)` grows to its content when the column is
> unconstrained and shrinks inside `max-height` when it is not […]
> `max-height:100%` resolves against the tab's definite row height and to
> nothing at all on Remote, where the column's parent has no definite height —
> so the single-column host keeps growing with the page as it always did.
> — `control-column.css:36-46`

The half of that comment about the Control tab is false as shipped; the half
about Remote is the constraint you must not break. A `1fr` track in a grid with
indefinite height should behave like max-content, which would satisfy both, but
**measure `/facilitator` directly** rather than reasoning about it — a Remote
view that suddenly stretches to the viewport, or stops growing with the page,
is a worse regression than the bug being fixed.

While you are here, decide whether the column should also gain the horizontal
counterpart's honesty: `#control-column-host` is `overflow-x: auto` /
`overflow-y: hidden` (`style.css`, the Control-tab block), and the `hidden` is
what turns this from a visible overflow into an invisible one.

## Fix the comment too

`control-column.css:36-46` asserts behaviour that has never been true. Whatever
lands, the comment must describe what the code does. This is the class of thing
`52` flagged: correct-looking code with a sincere comment claiming a guarantee
it never provided.

## Verify

A living browser check, in the nearest Control-tab journey
(`tests/verify_control_tab.py`).

The assertion is **not** "the cards element has `overflow-y: auto`" — it has
had that all along and it means nothing. Assert the measurable consequence:

```
scrollHeight > clientHeight   when the content overflows
```

and that scrolling actually moves it (`scrollTop` changes, and the last card's
bounding box comes into the host's box).

Fail it against the current tree first — it will report
`1408 === 1408` — so it is a guard and not a description.

Two notes:

* **gotcha 24** — a `set_content`/`page.route` fixture that does not load
  `control-panel.css` measures every metric as zero, because `--row-h`,
  `--gap`, `--pad-panel` and the rest are declared at `:root` there. A
  before/after that reads `0px -> 0px` passes vacuously. Use the real app.
* Force the overflow from the **manifest**, not from the target count — a
  40-param fixture with one target is the honest reproduction and stays valid
  if `2-multi-target-model` collapses the cards into one panel.
