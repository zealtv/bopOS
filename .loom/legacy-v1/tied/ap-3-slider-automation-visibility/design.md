# ap-3 — clearer automated-slider indication (single design pass)

Amendment to the ratified `automation-4` treatment, at Bob's 2026-07-20 request
(instructions.md part 3). Revises **Layer 3 (the value marker) only**; Layers 1
(kind glyph) and 2 (track tint / fade) of the judgment stand except where noted.
Authority for the rest remains `.loom/tied/automation-4-waveform-ux-gate/judgment.md`.

## 1. Chosen treatment (two sentences)

Replace the tiny 4×8px dot with a **full-row-height moving "highlight band"** — a
solid `--auto` pill (~34px tall, ~12px wide, rounded) that rides the value axis
behind the slider's touch point, using the *exact* `transform: translateX()`
keyframe mechanism already in place (GPU-cheap, phase-anchored, reduced-motion
trivial). The band sits **behind** the native range input so the thumb draws on
top of it (Bob's "highlighted bar behind the slider that is moving"), and it is
rendered only for the deterministic periodic kinds (`sine/tri/saw/square/loop`) —
never `sh`/`drift`, and no longer for `fade` (the fade now moves the real thumb).

## 2. DOM / CSS spec

**Element.** Keep the existing `<span class="live-param-marker …">` inside
`.live-param-range-wrap`; keep every custom property JS already sets
(`--auto-period`, `--auto-elapsed`, `--auto-min-pos`, `--auto-max-pos`,
`--auto-pNNNNN`, `--auto-loop-easing`) and every `@keyframes auto-*` **unchanged**.
Only the marker's own box and its `::after` change.

**Layering (z-index within `.live-param-range-wrap`).** Move the band *behind* the
input:
- `.live-param-range-wrap::before` (static 2px track tint) — `z-index:0` (unchanged).
- `.live-param-marker` (the band) — **change `z-index:3` → `z-index:1`**.
- `input[type=range]` — `z-index:2` (unchanged); its opaque thumb now rides over
  the band. Input `background` stays transparent so the band shows through the
  track. The band is deliberately much taller than the native groove, so it is
  never fully occluded.

**Band geometry.** Rewrite `.live-param-marker::after`:
```css
.live-param-marker::after{
  content:"";
  position:absolute;
  left:0; margin-left:-6px;        /* centre the 12px band on the value position */
  top:calc(50% - 17px);
  width:12px; height:34px;
  border-radius:6px;
  background:var(--auto);
  box-shadow:0 0 0 1px var(--panel);   /* 1px separation from track, no alpha wash */
}
.live-param-marker.free::after{        /* free LFO: shape/rate honest, phase not claimed */
  background:transparent;
  border:2px solid var(--auto);
  box-shadow:none;
}
```
The `.live-param-marker` wrapper keeps `width:100%; transform:translateX(var(--auto-min-pos)); animation-*`
as-is — only remove/adjust its `height`/`top` if needed so the taller `::after`
is not clipped (wrap already `overflow:hidden` at 44px; 34px fits).

**Animated properties.** `transform` (band position, via the untouched keyframes)
and `opacity` (state transitions) **only** — no `width`/`left`/`top` animation.
Compositor-friendly, honours the existing negative-`animation-delay` phase anchor.

**States.**
- **offline** (`.automation-offline .live-param-marker`): **hide the band**
  (`opacity:0`) instead of parking it at min-pos — a big bar frozen at min lies
  about the value. The dimmed glyph + static track tint carry "automated". (Replaces
  the current `animation-play-state:paused` + desaturate for this selector.)
- **muted** (`.automation-muted .live-param-marker`): **keep moving**, desaturate
  (`filter:saturate(.15)`) — unchanged; honest to the device still running it.
- **take-over** (`.taking-over .live-param-marker`): `animation-play-state:paused`
  then `opacity:0` over 180ms — unchanged.
- **reduced-motion**: extend the existing `@media(prefers-reduced-motion:reduce)`
  block to add `.live-param-marker{opacity:0}` (a paused full-height band parked at
  min is misleading); glyph + track tint remain the indicator. Keep the existing
  `animation:none`.
- **mixed aggregate**: no band (unchanged — `automationModel` returns null on mix).

**Fade case.** Fades now animate the real thumb (separate JS, part 2). **Drop** the
`.live-param-fade-progress` width-fill entirely (it is the only `width`-animating
element and becomes redundant/contradictory with a moving thumb). A fade keeps: the
static `╱` glyph, the static 2px `--auto` track tint, and the `→ target` `<output>`.
When the fade completes the model clears to plain (unchanged).

## 3. Kept / removed vs current treatment

- **Kept:** all `@keyframes auto-*`, all `--auto-*` custom props, the JS
  `automationModel`/`paramControl` marker-emission path, the static Layer-1 glyph,
  the static Layer-2 2px track tint, take-over freeze-then-drain, the `--auto` token
  pair (the coming bop.casio~ pass retints `--auto` → pale-cyan value-field hue at
  the `:root`/`data-theme` declarations only; no per-rule colour here).
- **Enlarged:** marker `::after` 4×8px dot → 12×34px band; centred on value.
- **Re-layered:** marker `z-index:3` → `1` (behind the thumb).
- **Removed:** `.live-param-fade-progress` element + `@keyframes auto-fade-progress`
  + its JS emission (line ~207–208); offline no longer parks the band (hides it);
  reduced-motion now hides the band.
- **JS delta:** in `paramControl`, stop emitting the fade `progress` span (`motion =
  marker` only). Marker emission, styles, and `free` class stay as written.

## 4. Rejected alternatives

- **VU-style value-axis fill that grows/shrinks** — animating `width` (or `scaleX`,
  which smears the fill) reads as "level" not "position", and 12 pulsing bars is
  maximal clutter; loses the value-position meaning the slider already owns.
- **Moving translucent "window" highlight** — low-alpha washes die in daylight and
  invert wrong on the light theme (judgment §theme); a solid band is more legible.
- **Keep the dot, just enlarge to a pill on top (z-index 3)** — an on-top marker
  fights the finger and the thumb for the same pixels; behind-the-thumb is Bob's ask
  and calmer.
- **Trailing/comet glow behind the band** — extra painted alpha per row, multiplies
  clutter across many simultaneous LFOs for no legibility gain over a solid band.
- **Restyle fade progress instead of dropping it** — two progress signals (thumb +
  bar) for one fade is redundant and the width animation is not transform-friendly.
