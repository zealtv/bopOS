# Semantic message pills — design proposal

Status: **ratified by Bob, 2026-07-23.** No `show.js` or CSS implementation had
started when this decision was accepted.

## Recommendation

Use **eight flat categories**, including `param-loop`. The omission of loop
from the seven-item list should be treated as an oversight: loop is selectable,
persists as a distinct generator, and behaves differently from value, fade,
LFO, and stop. Folding it into another colour would make the palette less
semantic at the exact point where the data model is already explicit.

Keep the pill's current full tinted fill, replace the arbitrary hash with the
semantic category, and add a compact visible kind code immediately after the
drag handle:

```text
⋮ CUE  blackout
⋮ PT   listener/0
⋮ RAW  /notify identify
⋮ VAL  gain 0.8
⋮ FD   gain 0.2 4s
⋮ LP   pan 0↔1
⋮ LFO  tremolo sine
⋮ STOP tremolo
```

The colour makes repeated rows scannable at normal desktop reading distance;
the code makes category recognition independent of colour. The full category
also goes in the button's accessible name and title.

## Alternatives considered

### A — tinted pill plus visible kind code — recommended

```text
[⋮ CUE blackout] [⋮ FD gain → .2] [⋮ LFO pan]
```

- **Density:** costs roughly 18–30 px per pill, but reads without inspecting
  tiny decoration. Keep the code fixed and ellipsize only the message label.
- **Themes:** each theme gets its own background/foreground token pair.
- **CVD:** hue confusion does not erase the `CUE`/`FD`/`LFO` code.
- **Focus/drag/drop:** category does not own border or box-shadow. Existing
  focus border/inset shadow and drop shadows remain unambiguous; the existing
  leading `⋮` remains the drag affordance.
- **Failure mode:** fewer alias characters fit at narrow widths. This is the
  acceptable trade: meaning should survive truncation, while the full message
  remains in the title/inspector.

### B — neutral pill with a leading colour swatch

```text
[⋮ ▌ blackout] [⋮ ▌ gain → .2] [⋮ ▌ pan]
```

- **Density:** preserves more label width.
- **Themes:** one strong mark colour is easy to tune.
- **CVD:** poor without adding a second legend or code; eight 3 px swatches are
  not reliably distinguished in peripheral vision.
- **Focus/drag/drop:** the leading swatch competes directly with the `⋮` drag
  affordance and with left/right drop markers.
- **Failure mode:** the semantic signal becomes the smallest object in the
  row. Rejected.

### C — shape/stroke encoding

```text
[ CUE blackout ]  [ / / FD gain ]  [ ~ LFO pan ]
```

- **Density:** patterns become noise at 22 px high, especially beside text.
- **Themes/CVD:** can work without hue in isolation.
- **Focus/drag/drop:** spends border style and edge paint already owned by
  focus, drag, and drop state. Rounded-corner changes also make the dense row
  look like mixed control types.
- **Failure mode:** eight distinct, memorable shapes or strokes are too many.
  Rejected.

### D — mode colour plus generator glyph

```text
[param ↗ gain] [param ~ pan] [cue blackout]
```

- **Density/CVD:** the glyph helps, but the colour still means a different
  dimension from the glyph.
- **Failure mode:** restores the two-dimensional visual grammar Bob explicitly
  collapsed into one flat collection. Rejected.

## Category mapping

| Category | Code | Hue role |
| --- | --- | --- |
| `cue` | `CUE` | amber |
| `point` | `PT` | sky |
| `raw` | `RAW` | neutral grey |
| `param-value` | `VAL` | purple |
| `param-fade` | `FD` | blue |
| `param-loop` | `LP` | magenta |
| `param-lfo` | `LFO` | cyan/teal |
| `param-stop` | `STOP` | vermilion |

`point` remains distinct from `cue`, matching Bob's corrected enumeration.
`param-stop` uses vermilion rather than semantic success green. LFO's teal is
redundantly labelled and is separated from `--green` by both role and surface
treatment.

## Concrete tokens

Use semantic tokens, never hex values at call sites. The existing neutral
`--strong-line` remains the unfocused border; focus continues to replace it
with `--accent`.

| Category | Dark background | Dark text | Light background | Light text |
| --- | --- | --- | --- | --- |
| cue | `#33260f` | `#f5cf8a` | `#f8ead0` | `#6b470e` |
| point | `#102b38` | `#a9ddf4` | `#dceef8` | `#175b7e` |
| raw | `#23282d` | `#d4dbe0` | `#e8ebee` | `#444c53` |
| param-value | `#1e1a38` | `#c5baf7` | `#e7e2f6` | `#4c418d` |
| param-fade | `#102638` | `#a9d8f2` | `#dcecf7` | `#15557d` |
| param-loop | `#301b28` | `#f0b6d6` | `#f3e0eb` | `#713b57` |
| param-lfo | `#0f2b2b` | `#a8e9e7` | `#d9f1ef` | `#135f5c` |
| param-stop | `#331713` | `#ffb0a5` | `#f7dfdc` | `#7d3028` |

Token names follow
`--show-pill-<category>-bg` / `--show-pill-<category>-text`; for example,
`--show-pill-param-fade-bg`. Measured text contrast ranges from **9.32:1 to
11.05:1 dark** and **6.22:1 to 7.30:1 light**, all above WCAG AA for the 11 px
pill text.

The eight hues are not claimed to remain pairwise unique under every CVD
simulation; amber/vermilion and blue/purple can converge. The visible codes are
the deliberate redundant channel. Do not weaken them into tooltip-only text.

## Markup and state coexistence

Render:

```html
<button class="show-message-pill show-pill-param-fade" ...>
  <span class="show-pill-drag" aria-hidden="true">⋮</span>
  <span class="show-pill-kind" aria-hidden="true">FD</span>
  <span class="show-pill-label">gain 0.2 4s</span>
</button>
```

- `.show-pill-label` owns ellipsis and may shrink; `.show-pill-kind` does not.
- The accessible name begins with the expanded category, such as
  “parameter fade: …”.
- Category classes set only background and foreground tokens.
- `.focused` continues to own `border-color` and inset `box-shadow`.
- `.show-drop-before/after` continues to own directional `box-shadow`.
- `.show-pill-drag` stays the first visible item and keeps its drag semantics.
- Semantic `--green`, status red/amber, and app accent tokens are unchanged.

The old `show-pill-0..7` classes and `PILL_PALETTE_SIZE` are removed completely.
Identical categories intentionally look identical; alias/message text supplies
within-category identity. Retaining a residual hash would make colour mean two
things again.

## Ratification

Bob accepted:

- eight categories, with `param-loop` restored;
- full tint plus visible kind code;
- the code labels (`CUE`, `PT`, `RAW`, `VAL`, `FD`, `LP`, `LFO`, `STOP`);
- the palette/token table above.
