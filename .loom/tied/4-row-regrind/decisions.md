# 4-row-regrind — decisions and evidence

Authority: the tied `2-control-panel-design` stitch (`control-panel-design.md`
§3 mapping table, `design-language.md` §§5–8, `mockup-control-panel.html`).

## What shipped

`dashboard/static/js/control-surface.js` + `dashboard/static/css/control-panel.css`:

- **The row is `[value box 58px][name-in-slider][∿ 18px]`.** Numeric rows are a
  three-column grid; the parameter name moved *inside* the slider trough.
- **The native `<input type=range>` is still the interactive element.** It is
  `appearance:none` with a transparent track and a 1px transparent thumb,
  absolutely positioned over a wrapper that paints trough, fill, marker line
  and name. No pointer, keyboard, takeover, precision-entry or ARIA behaviour
  was rewritten.
- **`--v` is the fill/marker position**, set at render from
  `ParamSpec.position` and kept in step by `syncFill()` — called from the drag
  handler, the precision-field commit and the fade rAF.
- **Value boxes**: floats left-align, integers right-align (`data-integer`).
- **Mixed** is one 45° slash pattern in two inks: `--hatch` normally,
  `--mod-hatch` when a generator is anywhere in the aggregate (new `mixed-mod`
  row class). The value box hatches and shows `·····`.
- **The `value ▸ gen` switch is retired.** The ∿ icon is the disclosure
  (`aria-expanded`, same `openDrawers` keying) *and* the modulation indicator.
- **Drawer kind `<select>` → `LFO | loop | fade` latching tabs**, same
  `GEN_KINDS` and the same compile path.
- Takeover announcement path unchanged (Q4).

## Calls made inside the ratified design

1. **The animated marker carries the generator fill.** Under a periodic
   generator the CSS-animated `.live-param-marker` is the only element that
   knows where the value is between heartbeats, so its `::after` is the marker
   line and its `::before` is the fill extending left to the trough edge
   (clipped by the wrap). The static fill and static marker are hidden behind
   `:has(.live-param-marker)`. Fades keep the static fill — the rAF already
   moves the input's value, so `syncFill` is enough.
2. **Reduced motion restores the static fill.** The shipping rule hides the
   animated marker, which would otherwise take the fill with it and leave a
   generator-driven row looking empty. Inside the reduced-motion query the
   static fill and marker come back: a stepped, per-heartbeat reading of the
   modulated value, which is what design-language §10 asks for.
3. **A free-running LFO's marker is a broken line.** The old hollow-vs-solid
   distinction does not survive at 1.5px, so `free` becomes a dashed marker
   rather than losing the distinction.
4. **The value box shows the value, not a legend.** The shipping readout
   packed `mixed` / `auto·mixed` / `0.4 · sine` / `→ 0.9` into the readout.
   In 58px that is illegible, and the ∿ icon plus cyan ink already say
   "modulated". The box now shows the live value (fades show their target);
   mixed shows the ratified dots. **The words moved to the box's
   `aria-label`** — `"<name>, mixed values"` / `"<name>, mixed automation"` —
   per design §3 ("the aria-labels keep the words"). The range input's own
   accessible name is unchanged.
5. **Coarse pointers get a taller row, not a different layout.** `--row-h`
   goes 24px → 34px under `(pointer:coarse)`, so the standalone facilitator
   keeps a touch target without forking the grammar.
6. **Scoped with `:has(.live-param-range-wrap)`.** Only numeric rows regrind;
   strings and 0/1 toggles keep the shipping flex row until
   `6-non-float-kinds`. They do get the ∿ icon, since the drawer is the same.

Out of scope by the ratified split: the drawer's *interior* layout (waveform
display, mini-sliders, `free` placement, full-width arg boxes) is still the
shipping builder — the split assigns only the kind tabs to this stitch.

## Verification

`tools/run-tests.sh browser` — **12/12 pass**. Journeys updated in this stitch:

- `verify_control_surface_component.py` — new row-grammar section: child order
  is `[output.live-param-value][.live-param-range-wrap][button.live-param-mod]`,
  name inside the slider, `--v` tracks the value (`0.2` float / `0.25` for a
  new integer `steps` param), dragging moves it to `0.8`, float/integer
  alignment, the range is a transparent overlay, a generator-driven row hands
  the fill to its marker (`::before` pseudo-element background) while a manual
  row keeps its own. Plus a mixed-aggregate takeover probe: hatched before,
  solid at the new value after, and the value reaches every member. The probe
  host is moved inside a real `.live-card` so the panel stylesheet applies and
  no heartbeat races the measurement.
- `verify_generator_drawer.py` — `value ▸ gen` assertions became ∿-icon
  assertions (disclosure state, one icon, closes on second click); the kind
  `<option>` list became the tab row (order + exactly one latched). New mixed
  presentation checks: dots + hatched box, hatch across the full trough width,
  no marker line, gray ink with no generator involved.
- `verify_device_control_panel.py`, `verify_manifest_param_visibility.py` —
  selector updates only (`[data-gen-mode="gen"]` → `[data-gen-toggle]`).

Screenshots (`after-*.png`; both themes, both hosts, drawer open), captured with
`shoot_control_panel.py` carried over from `3-tokens-and-chrome`. Fill inks
were pixel-sampled to confirm they are the tokens and not a stray paint:
trough `rgb(16,22,27)`, fill `rgb(40,45,50)` in dark.

## Not verified here

- **Drag and takeover *feel* is a hardware adoption check** (Finn Jet + Ciro
  Toast), per the design's §5. The thumb is now a hairline and the fill is
  painted rather than native, so latency and grab feel are judgment calls for
  Bob, not something this stitch claims.
- `tools/run-tests.sh fast` has **one failure that predates this stitch**:
  `test_device_control_routing.test_reappearing_physical_device_replays_persistent_enabled_state`
  fails under `unittest discover` and passes when that module runs alone —
  a suite-ordering/state-leak issue, reproduced on stashed clean `main`.
  Nothing in this stitch touches that path.
- `verify_live_param_checkbox.py` failed once in the first full-suite run and
  has passed every run since (four in a row, including in-suite). Recorded as
  observed flake, not as fixed.
