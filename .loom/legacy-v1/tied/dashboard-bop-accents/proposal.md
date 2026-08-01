# Proposal — bop accent palette for the dashboard

Author: UI accent pass, 2026-07-20. Scope: a token-level accent recolour of the
dashboard (`dashboard/static/css/style.css` + `facilitator.css`), drawing the
accent language from Bob's `bop.casio~` instrument aesthetic — **lavender +
periwinkle + ice cyan + occasional warm cream** — while the dark chrome stays
dark. This is an accent pass, not a reskin: `--bg/--panel/--line/--text/--dim`
are untouched, the semantic trio (`green/amber/red`) keeps its meaning, and the
ratified `--auto` token is left exactly as-is.

Grounded in: `style.css` (tokens + ~120 hardcoded hexes), `facilitator.css`,
`index.html` structure, and `.loom/tied/automation-4-waveform-ux-gate/judgment.md`
§"Theme portability" (the `--auto` token pattern and the anticipated
`data-theme` light theme, which this proposal mirrors token-for-token).

---

## 1. The bop accent palette (token pairs)

New tokens live at the top of `:root` in **both** stylesheets, right after the
existing base tokens, and follow the ratified `--auto` three-line pattern
(base = dark, `prefers-color-scheme: light` override, `data-theme` overrides
both ways) so the coming light theme is free.

Contrast measured with WCAG relative luminance against `--bg #101316`
(L≈0.0063) and `--panel #191e23` (L≈0.0126). Text targets ≥4.5:1; non-text
marks (rings, borders, fills, dots) target ≥3:1.

| Token | Dark | Light | Dark contrast (bg / panel) | Role | Passes |
|---|---|---|---|---|---|
| `--accent` (periwinkle) | `#8A82D8` | `#5A4FB8` | 5.6:1 / 5.0:1 | The primary interactive accent: selected-state borders + inset boxes, active tab edge, "on" chips, spatial point handles | text ✅ / mark ✅ |
| `--accent-bright` (lavender) | `#B9AFF2` | `#6A5FCF` | 9.3:1 / 8.3:1 | Focus-visible outlines only (must out-pop `--accent`) | mark ✅ |
| `--accent-soft` (pale lavender) | `#C9C3F2` | `#4B41A8` | 11.2:1 / 10.0:1 | Soft coloured labels/glyphs on dark where plain `--text` reads too cold — the reference panel lavender | text ✅ |
| `--accent-cyan` (ice) | `#8FE3DE` | `#1E8A84` | 12.6:1 / 11.3:1 | Slider fill (`accent-color`), value/readout emphasis, info marks — the reference cyan value fields | text ✅ / mark ✅ |
| `--accent-cyan-soft` (pale ice) | `#C9F2F0` | `#157773` | 13.9:1 / 12.4:1 | Optional pale readout text (`<output>`), cyan tick marks | text ✅ |
| `--accent-warm` (cream) | `#F2E4B0` | `#8A6D12` | 16.4:1 / 14.6:1 | Playful highlight, *sparingly*: checkbox/toggle `accent-color`, the "!" warning glyph if one is added | text ✅ / mark ✅ |
| `--sim` (harmonised blue) | `#6FB3E6` | `#2464A8` | 8.4:1 / 7.5:1 | Simulated-device indicators (dots/strokes). Pulled into the `--auto` blue family so it stops being a random `#5ea7ff` | text ✅ / mark ✅ |

Unchanged and still authoritative: `--auto` (`#7fb0e8` dark / `#2464a8` light —
automation), `--green` (online/running), `--amber` (crashed/paused),
`--red` (danger/mute). `--accent` (violet-leaning `#8A82D8`) is deliberately
distinct in hue from `--auto` (blue `#7fb0e8`) so an automation marker never
reads as "selected".

CSS block to add (identical in both files; `facilitator.css` omits the tokens
it doesn't use):

```css
:root{
  --accent:#8A82D8; --accent-bright:#B9AFF2; --accent-soft:#C9C3F2;
  --accent-cyan:#8FE3DE; --accent-cyan-soft:#C9F2F0;
  --accent-warm:#F2E4B0; --sim:#6FB3E6;
}
@media (prefers-color-scheme: light){:root{
  --accent:#5A4FB8; --accent-bright:#6A5FCF; --accent-soft:#4B41A8;
  --accent-cyan:#1E8A84; --accent-cyan-soft:#157773;
  --accent-warm:#8A6D12; --sim:#2464A8;
}}
:root[data-theme="dark"]{
  --accent:#8A82D8; --accent-bright:#B9AFF2; --accent-soft:#C9C3F2;
  --accent-cyan:#8FE3DE; --accent-cyan-soft:#C9F2F0;
  --accent-warm:#F2E4B0; --sim:#6FB3E6;
}
:root[data-theme="light"]{
  --accent:#5A4FB8; --accent-bright:#6A5FCF; --accent-soft:#4B41A8;
  --accent-cyan:#1E8A84; --accent-cyan-soft:#157773;
  --accent-warm:#8A6D12; --sim:#2464A8;
}
```

All accents are **solid** hues (no low-alpha washes) so they survive daylight
and invert correctly on the light theme — the same discipline the `--auto`
ruling mandated.

---

## 2. Mapping table — hardcoded accent → token

Every current hardcoded accent that carries *interaction/identity* meaning.
Structural greys (`#10161b`, `#12171c`, `#14191d`, `#0f1418`, `#273039`,
`#45515b`, `#52616c` panel/input/button chrome) are **left alone** — they are
the dark surface, not accents (see §4).

### Selected / focused state (currently near-white `#e8edf1` / `#f5f7fa` / `#fff`)

| Location (file:line-ish) | Current | → Token |
|---|---|---|
| `button/summary/input:focus-visible` outline (style 41) | `#f5f7fa` | `--accent-bright` |
| `.node:focus-visible .element-dot` stroke (style 40) | `#fff` | `--accent-bright` |
| `.group-legend-chip.focused` border + inset box (style 38) | `#e8edf1` | `--accent` |
| `.group-row.focused` border (style 38) | `#75828d` | `--accent` |
| `.show-step-row.focused`, `.show-message-pill.focused` border+box (style 51) | `#e8edf1` | `--accent` |
| `.show-divider-row.focused` outline (style 52) | `#e8edf1` | `--accent` |
| `.show-target-chip.on` border + inset box (style 52) | `#e8edf1` | `--accent` |
| `.show-target-chip.on` background (style 52) | `#26303a` | keep (neutral raise) |

### Tab / segmented "selected" edges (currently neutral `#45515b` / `#52616c` / `#2b3740`)

| Location | Current | → Token |
|---|---|---|
| `.primary-tabs button[aria-selected]` border (style 28) | `#45515b` | `--accent` |
| `.execution-options button[aria-pressed]` inset box (style 28) | `#52616c` | `--accent` |
| `.sidebar-tabs button[aria-selected]` border (style 38) | `#52616c` | `--accent` |
| `#live-scope-tabs button[aria-selected]` border (facilitator 12) | `#45515b` | `--accent` |
| Selected fills (`#273039` / `#2b3740`) behind all of the above | — | keep (neutral fill; the accent is the edge, not the fill — keeps the tab strip calm) |

### Spatial view — points & sim (currently `#5ea7ff` blue + `#dcecff`)

| Location | Current | → Token |
|---|---|---|
| `.point-radius` stroke/fill default (style 3) | `#5ea7ff88`/`#5ea7ff12` | `--accent` (per-point `--point-colour` still overrides) |
| `.point-handle` fill default (style 3) | `#5ea7ff` | `--accent` |
| `.point-handle` stroke (style 3/14) | `#dcecff`/`#f5f7fa` | keep neutral (light outline for contrast on any point hue) |
| `.dot.sim` bg + glow (style 17) | `#5ea7ff` | `--sim` |
| `.node.sim .element-dot` stroke (style 17) | `#5ea7ff` | `--sim` |
| `.space-origin` cross (style 15) | `#ff7380`/`#ff9aa4` | keep (origin marker reads as a soft red landmark; not brand) |
| `.listener-*` puck (style 4) | `#f5f7fa` + `#45d483` tip | keep (physical listener is intentionally neutral white; green tip = heading semantic) |

### Sliders & toggles (the signature bop move)

| Location | Current | → Token |
|---|---|---|
| `.live-param input[type=range]` `accent-color` (facilitator 22) | `--green` | `--accent-cyan` |
| `#master-control input` `accent-color` (style 13/28) | `--green` | `--accent-cyan` |
| `.live-param input[type=checkbox]` `accent-color` (facilitator 42) | `--green` | `--accent-warm` |
| `.membership-check input`, `.seat-row input:focus` border, misc range `accent-color` (style 17/39) | `--green` | `--accent-cyan` (range) / `--accent-warm` (check) |

Rationale: ice-cyan value fields + cream toggles are the two most recognisable
`bop.casio~` cues, and moving them off `--green` **frees green to mean only
online/running** everywhere else (dots, progress fills, `show-remaining`). This
is the single highest-identity change and it is one property per selector.

### Show pills (8) and target-group swatches (4) — categorical, mostly KEEP

| Location | Current | → Decision |
|---|---|---|
| `.show-pill-0..7` (style 51) | 8-colour ramp | **Keep** as a categorical set (message-index identity, not brand accent). Only retune `.show-pill-0` toward the cyan family (`#3e7ba3/#122736/#9fd4f5` → cyan-leaning) so the "first/primary" pill echoes bop, and keep 1–7 as-is. See §4. |
| `.show-target-group.slot-0..3 .show-target-swatch` (style 52) | Okabe-Ito `#56B4E9/#E69F00/#00B98B/#CC79A7` | **Keep unchanged** — colour-blind-safe ratified set; tiny swatches doing categorical work. |
| `--group-colour` default `#59636b` + slot dash/dot styles (style 38/40) | neutral grey | **Keep** (group identity colour is data-driven per group). |

### Semantic glows & danger (KEEP, meaning-bearing)

| Location | Current | → Decision |
|---|---|---|
| `.dot.online` / heartbeat glow (style 1/12) | `--green` glow | Keep |
| `.danger.active` red glow (style 1, facilitator 45) | `#ff4e5d88` | Keep |
| `.device-mute-indicator.fleet` etc. red family (style 19) | `#a3414a/#ff9da6/#35171b` | Keep (mute severity) |
| patch/asset state badges green/amber/red families (style 21/47) | green/amber/red tints | Keep (sync-state semantics) |
| `#declared-cues .scheduling`/`.triggered` (facilitator 11) | green cue-lead ramp | Keep (green = firing) |

---

## 3. Before/after — the five highest-impact spots

**1. Header + primary tabs.** *Before:* the selected tab is a grey pill
(`#273039` on `#45515b` border) — indistinguishable from an unpressed button at
a glance on a tablet. *After:* the selected tab keeps its grey fill but gains a
periwinkle `--accent` border/underline; `:focus-visible` rings across the whole
app switch from cold near-white `#f5f7fa` to lavender `--accent-bright`. Net:
"where am I / what's focused" now speaks bop, and the header chrome itself is
untouched.

**2. Live cards (Dashboard/facilitator).** *Before:* every slider fill is green,
colliding with the green online-dot right above it in the same card. *After:*
sliders fill ice-cyan (`--accent-cyan`), the int toggle fills cream
(`--accent-warm`), and green is reserved for the status dot and
`show-remaining`. A card now reads as "green = is it alive, cyan = its value,
cream = its switch" — three distinct jobs, three distinct hues, exactly the
`bop.casio~` panel logic.

**3. Show rows & pills.** *Before:* focused row/pill and "on" target-chip all
use white `#e8edf1` inset boxes — sterile, and easy to lose in a dense Ableton
row. *After:* selection is periwinkle `--accent`; the 8 message pills stay their
categorical selves (only pill-0 nudged cyan for cohesion). The Show tab stays
calm because only the *selection* recolours, not the content — no rainbow added.

**4. Spatial view.** *Before:* draggable points and their radius rings are a
generic `#5ea7ff` blue, the same blue as the sim indicator, so "a point" and "a
simulated device" look related when they aren't. *After:* points become
periwinkle `--accent` (per-point `--group-colour` still wins when set), while
sim indicators move to `--sim` in the `--auto` blue family — points and
simulation are now visibly different systems. Physical landmarks (listener puck,
origin cross) stay neutral on purpose.

**5. Buttons / focus / selected chips.** *Before:* focus + selected states are
all cold whites/greys, reading corporate. *After:* one consistent accent grammar
— `--accent-bright` = "focused right now", `--accent` = "selected/active",
`--accent-cyan/-warm` = "this is a live value/switch". The base button surface
(`#273039` on `#45515b`) is unchanged, so nothing gets louder — the accents just
gain a bop identity.

---

## 4. What NOT to change, and why

- **`--bg / --panel / --line / --text / --dim`** — the dark surface is the point;
  pastels arrive as accents on top. Nudging them violet would fight the coming
  daylight-legibility goal and muddy the pastels' contrast. Left verbatim.
- **`--green / --amber / --red`** — semantic. Green = online/running, amber =
  crashed/paused, red = danger/mute must stay instantly recognisable across
  fleet ops. (Optional micro-nudge deferred to an open question; not part of the
  shipping diff.)
- **`--auto` (`#7fb0e8`/`#2464a8`)** — freshly ratified in automation-4; this
  proposal is explicitly built to not collide with it (violet `--accent` vs blue
  `--auto`).
- **Target-group Okabe-Ito swatches** (`#56B4E9/#E69F00/#00B98B/#CC79A7`) — a
  ratified colour-blind-safe categorical set. Recolouring them toward pastels
  would break that guarantee for a few 10px swatches. Untouched.
- **The 8 Show pills (1–7)** — categorical message identity; a bop-tinting pass
  risks collapsing their distinctness ("don't rainbow it" cuts both ways — the
  categorical ramp is *already* doing a legitimate job). Only pill-0 harmonised.
- **Structural greys** (`#10161b` inputs, `#14191d` sub-panels, `#273039`
  buttons, `#45515b/#52616c` borders) — these are dark chrome, not accents.
  Touching them is a reskin, not an accent pass, and would blow the "one stitch,
  mostly token-level" budget.
- **Physical/landmark marks** — listener puck (`#f5f7fa`), space-origin cross
  (`#ff7380`) — deliberately neutral/semantic; not brand surface.

---

## 5. Implementation plan (one stitch, mostly token-level)

Bounded to two CSS files. No JS, no HTML, no `.pd`. Order:

**Step A — declare tokens.**
- `dashboard/static/css/style.css` `:root` — add the seven `--accent*/--sim`
  tokens + the `prefers-color-scheme` / `data-theme` blocks from §1.
- `dashboard/static/css/facilitator.css` `:root` — add the subset it uses
  (`--accent`, `--accent-bright`, `--accent-cyan`, `--accent-warm`, `--sim`).

**Step B — migrate hardcoded hex → token (find/replace, per §2).**

*`dashboard/static/css/style.css`:*
- focus-visible outline `#f5f7fa` → `--accent-bright` (line ~41); `.node:focus-visible` `#fff` → `--accent-bright` (line ~40).
- `.group-legend-chip.focused`, `.group-row.focused`, `.show-step-row.focused`, `.show-message-pill.focused`, `.show-divider-row.focused`, `.show-target-chip.on` selection `#e8edf1`/`#75828d` → `--accent` (lines ~38, 51, 52).
- `.primary-tabs [aria-selected]`, `.execution-options [aria-pressed]`, `.sidebar-tabs [aria-selected]` selected edges → `--accent` (lines ~28, 38).
- `.point-handle` / `.point-radius` default `#5ea7ff*` → `--accent`; `.dot.sim` + `.node.sim` `#5ea7ff` → `--sim` (lines ~3, 14, 17).
- `#master-control input` `accent-color:var(--green)` → `--accent-cyan` (lines ~13, 28).
- `.membership-check input` `accent-color` → `--accent-warm`; `.seat-row input:focus` border → `--accent-cyan` (lines ~17, 39).
- `.show-pill-0` trio → cyan-leaning (`--accent-cyan-soft` text / darker cyan bg+border); pills 1–7 unchanged (line ~51).

*`dashboard/static/css/facilitator.css`:*
- `input[type=range]` `accent-color:var(--green)` → `--accent-cyan` (line ~22).
- `.live-param input[type=checkbox]` `accent-color:var(--green)` → `--accent-warm` (line ~42).
- `#live-scope-tabs button[aria-selected]` border `#45515b` → `--accent` (line ~12).
- `#technical-link`/header stays neutral (no change).

**Step C — verify.** Copy the newest tied `verify_*.py` (repo-by-marker root,
sim ports, `~/.venvs/bopos` venv, headless chromium). Assert: (1) a focused
control's `outline-color` computes to the `--accent-bright` value; (2) a range
input's `accent-color` computes to `--accent-cyan`; (3) a selected Show
step/target chip border computes to `--accent`; (4) contrast spot-check of
`--accent`/`--accent-cyan` text vs `#101316` ≥4.5:1 (compute in-test). Add a
`data-theme="light"` toggle assertion that the same tokens resolve to their
light values, so the pass is proven theme-portable ahead of the light theme
landing. Reduced-motion is unaffected (no new motion introduced).

The whole diff is ~2 token blocks + ~20 single-value substitutions across two
files — reviewable as a token diff, no structural churn.

---

## 6. Open questions for Bob

1. **Sliders cyan / toggles cream** — this is the boldest identity move (moving
   `accent-color` off `--green`). Ratify, or keep sliders green and let the
   accents live only in selection/focus/points? (Recommend: do it — it's the
   most `bop.casio~` cue and it de-conflicts green.)
2. **Value readouts** (`<output>`) — leave neutral `--text` (calm), or tint with
   `--accent-cyan-soft` to echo the cyan value fields? (Recommend: leave neutral
   for now; cyan sliders already carry the cue and all-cyan risks noise.)
3. **Amber temperature** — retune `--amber #f2b84b` a hair warmer/creamier to sit
   in the bop family, or leave it (it's load-bearing crashed/paused semantic
   across many badges)? (Recommend: leave; a warm nudge is a separate, riskier
   pass.)
4. **Show pill-0 nudge** — OK to harmonise only pill-0 toward cyan, or leave the
   whole 8-ramp untouched for categorical stability?
5. **Focus-ring hue** — lavender `--accent-bright` for *all* focus rings, or keep
   the near-white ring for maximum daylight pop and use lavender only for
   *selected* (non-focus) states? (Recommend: lavender — it still tests 9.3:1.)
6. **Light-theme surface values** — the accent *light* values are proposed
   against an assumed `~#f4f5f7` light bg; when the light theme lands its actual
   surface tokens may shift these by a few points. Treat the light column as
   provisional until the `data-theme` surface palette is ratified.
