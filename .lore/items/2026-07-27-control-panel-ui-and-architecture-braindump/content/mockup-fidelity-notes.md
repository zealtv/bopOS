# Mockup fidelity notes — read before matching the image

Added 2026-07-30, when Bob re-shared the Excalidraw and set the standard:
*"the excalidraw I think should be the guiding north star, the closer we can
match it the better."*

That standard needs one qualifier. The mockup is from 2026-07-27. Several of
its details were **superseded by Bob's own later rulings**, so matching it
uncritically would reintroduce retired features. This file is the diff.

## The image itself

**`content/mockup.png` — on file since 2026-07-30** (3409 × 1408 PNG, supplied
by Bob). The `.excalidraw` source is not in the repo; add it if it survives.

Two companions, both still useful:

1. `.loom/tied/2-control-panel-design/mockup-control-panel.html` — the living
   HTML prototype, reviewed by Bob. It is *ahead* of the image wherever the
   rulings below apply, so for behaviour it outranks the PNG.
2. `braindump.md` in this folder — the verbatim annotation text.

## Sampled palette (light)

Measured off `mockup.png`, 2026-07-30. This settled a real drift: the shipped
light theme had made the panels pink. Bob: *"the pink is a little heavy on the
control panel — notice how it's used in the Excalidraw mockup. It's a
background that panels sit on, not the colour of panels themselves."*

| role | mockup | shipped token |
|---|---|---|
| page ground | `#f8f0fc` | `--cp-bg` / app `--bg` — **the only pink token** |
| panel body | `#f8f9fa` | `--cp-panel` |
| subpanel, drawer, manual slider fill | `#e9ecef` | `--cp-subpanel`, `--value-fill` |
| value boxes, troughs, button faces | `#ffffff` | `--cp-input`, `--cp-control` |
| ink (text and borders) | `#1e1e1e` | `--cp-text` `#212529`, `--cp-control-line` `#495057` |
| cyan fill | `#99e9f2` | `--mod-fill` — **delta, unresolved** (see below) |

The greys are Open Color `gray-0/1/2` — Excalidraw's own defaults — so the
mockup's character is *neutral scale plus one cyan on a pale pink ground*.

The cyan is the one open delta: `--mod-fill` at `rgba(7,152,188,.20)` renders
lighter over white than the mockup's `#99e9f2`. Not changed, because the cyan
was ratified 2026-07-27 and Bob raised no objection to it on review.

## Superseded by later rulings — do NOT copy from the image

| In the mockup | Superseded by |
|---|---|
| Per-event `sync` button beside each `send` (cyan on `event[1]`/`event[2]`, grey on `event[3]`) | **Every event forward-syncs** (Bob, 2026-07-27). The per-row `sync` button is dropped; a global lead time of `0` *is* sync-off. `04-event-fire-affordance` further replaced the row's `send` with a 58 × `--row-h` panel object carrying the lead sweep and fire flash. |
| Event rows labelled `event[1]`, `event[2]`, `event[3]` — per-element indexing implied | Event elements are **free-form labeled floats**, arity 1–3, note/velocity/duration by convention only. Per-element `labels` were then retired outright in **contract v1.16** (2026-07-28). |
| `enum` row drawn as a distinct kind, with a "we may at a later time want enumerators" note in the annotation | Enums shipped as `options` on an **integer** param. Toggles likewise are `type: "i"`, `min: 0`, `max: 1`. Events were the only genuinely missing kind (Bob, 2026-07-27), and the manifest now carries an explicit **`kind`** field (contract v1.14/v1.15 hard break). |
| Toggle drawn flashing its live value under a generator; annotation asks for the same on sample-and-hold and drift | **Partly superseded** (Bob, 2026-07-27, live review; `8-kind-feedback-pass`). A control that cannot show its generator's real value must not animate a substitute. The toggle flash and the invented value-box number are retired wherever they would be fabricated; those controls **pulse the modulation ink** and the box shows mixed dots. What survives unchanged: the marker-bearing slider and the rAF-sampled fade, both of which do show the exact value. |
| Preset row (`preset 1 ▾` + `new` / `save` / `del`) — annotated as "provisional thinking ahead of the preset system" | Superseded by the ratified design in `.loom/tied/1-preset-architecture-design/` and shipped in `41-preset-primitive`. A preset is not a wire concept; entries are `/p/<identity>` argument lists stored sparsely per patch. Presets do **not** capture events. The shipped row is authority over the mockup's sketch. |
| `<target>/e/*` proposed tentatively in the annotation | Ratified and shipped as the `/e/*` event plane, **contract v1.14**, with the `"0"` fire-on-arrival sentinel. `/cue` was retired outright in **v1.15**; cue firing is an event with zero elements, fired from the control panel's events section. |
| Events and Parameters ordering (mockup shows floats first, non-float kinds in a separate right-hand panel) | Events now render **above** Parameters, both on the panel and in the manifest editor (`04-event-fire-affordance`, Bob's 2026-07-28 review). |

## Still authoritative — match these closely

- **Overall character**: tight, compact, monospace, grayscale plus cyan.
  Heritage is Pure Data, Ableton, MaxMSP. Congruence with bop in PD is a
  design goal, not a nicety — the same person patches and operates.
- **The parameter row grammar**: `[value box 58px][name-in-slider][∿ 18px]`,
  one parameter per line, never taller than `--row-h`.
- **Name inside the slider**, left-aligned — PD's `label: value` idiom.
- **Cyan = modulation** first, selection second. `04-event-fire-affordance`
  widened this to "something is driving this, continuously or discretely",
  which is why the event fire button is cyan.
- **Mixed-state hatching**: one pattern (45° slashes), two inks — grey for
  mixed values, cyan when a generator is involved anywhere in the aggregate.
  The mockup's `delay/time` and `delay/wet` rows are the reference. (The
  annotation says "crosshatching"; the ratified rule is slashes, and
  crosshatch is explicitly out.)
- **Hierarchy accordions**: `▶ reverb` collapsed, `▼ delay` expanded.
- **Drawer layouts**: LFO — waveform display with shape select inside it,
  side column of `phase`/`curve` mini-sliders, `free` toggle below `curve`,
  args row `min` `max` `period` `[unit ▾]`. Fade — curve display, `from` box
  and `curve` mini-slider, segment rows `to [v] in [n] [unit ▾] (remove)`,
  `add segment`.
- **Button shapes from PD**: a bang is a circle (momentary, 7px), a toggle is
  a square box (latching, 1px).
- **Light theme is pink.** The mockup's pale pink ground is where
  `--bg: #f4d7eb` comes from; it is deliberate, not an Excalidraw default.

## New in the 2026-07-30 reading

Two details worth naming that the earlier transcription passed over:

- The panel header is `All Seats` with a **`send all`** momentary button at
  top right — a panel-level action, distinct from any per-row control. Its
  role under the shipped preset system should be checked rather than assumed.
- The mockup panel is **narrow** — roughly a single column, which is the
  visual argument behind Bob's 2026-07-30 ruling that the Control tab should
  host N columns rather than one wide panel, and that the Show inspector (also
  a narrow column) can host the same components.
