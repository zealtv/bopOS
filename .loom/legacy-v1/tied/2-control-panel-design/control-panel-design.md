# Control-panel design — RATIFIED 2026-07-27 (live session with Bob)

The mockup-driven design for the Control tab's control panel, per Bob's
2026-07-27 braindump (lore `2026-07-27-control-panel-ui-and-architecture-braindump`)
and the live review session of the same day. Companion files:

- `design-language.md` — the extrapolable rules/tokens (the rollout input).
- `mockup-control-panel.html` — the living prototype, reviewed and
  iterated with Bob in-session; the visual authority.

Scope: the shared `ControlSurface`
(`dashboard/static/js/control-surface.js`) and its hosts — the Control tab
iframe and the Device-tab control panel. **Evolve, don't fork** (standing
constraint: the system works and must keep working). The standalone
facilitator keeps its tablet-first chrome; it consumes the same
`ControlSurface` rows, so it inherits behavior changes but its layout
constraints stay separate.

## 1. Panel anatomy (top to bottom)

1. **Header**: target name (e.g. `All Seats`, a group, a seat) + momentary
   `send all` (replays current values to the target — the existing per-scope
   replay affordance).
2. **Patch + preset row**: patch name; preset dropdown + `new`/`save`/`del`.
   **Provisional**: this is a designed slot, not built behavior — presets are
   `41-preset-primitive`. Until 41 lands the row renders with the dropdown
   disabled and the patch name live. The slot exists now so 41 doesn't have
   to redesign the panel.
3. **Parameter rows**, one per line, in manifest order, showing the FULL
   manifest (the shipped `1-full-manifest-visibility` ruling; `dashboard:`
   gates only the facilitator view).
4. **Hierarchy accordions** for nested addresses, children indented.
5. **Generator drawers** inline beneath their row when open.

Row grammar, state inks, drawer layouts, button shapes, focus, palette:
all specified in `design-language.md` §§5–10. This document does not repeat
them; it maps them onto the shipping code.

## 2. Parameter kinds

| manifest kind | control | wire | automation |
|---------------|---------|------|------------|
| float | value box + slider + ∿ | `/p/*` float | full §3.2 |
| integer | value box + slider (step 1) + ∿ | `/p/*` int | §3.2 (values quantized node-side as today) |
| toggle (int 0/1) | latching button + ∿ | `/p/*` 0\|1 | §3.2; UI flashes live value under a generator |
| enum | select + ∿ | `/p/*` int index | **automate like ints** (Q2 ruling) — generators emit indices, quantized like integer params |
| string | text box, no ∿ | `/p/*` string | none (unchanged) |
| **event** | 1–3 value boxes + `sync` toggle + `send` momentary | **future `<target>/e/*` plane** | forward-sync via cue lead time |

**Events are a contract question, not part of this implementation.** The UI
shape is specced here (single = note, pair = note+velocity, triplet =
note+velocity+duration; `sync` latches forward synchronization on the row,
`send` fires) so `44-event-plane` designs the wire against a known surface.
This thread builds the event row **only** as far as rendering a manifest
declaration, disabled, if 44 hasn't landed — no `/e/*` messages are sent.

## 3. Mapping onto the current `ControlSurface`

What exists stays load-bearing; the changes are mostly presentation:

| current | becomes |
|---------|---------|
| `<label>` row: name+glyph, `value ▸ gen` mode switch, `<output>` readout, native `<input type=range>` | grid row: value box (the precision `<output>`), custom slider (name inside, fill + marker), ∿ icon button |
| `value ▸ gen` two-button mode switch | the ∿ icon (open/close drawer); "which am I editing" collapses into drawer-open state — same `openDrawers` keying |
| drawer `generator <select>` kind picker | `LFO | loop | fade` tab row (same `GEN_KINDS`, same compile path) |
| drawer Apply/Stop buttons | retained (momentary); Apply on a running generator re-applies, idempotent for synced LFOs as today |
| mixed → placeholder text `mixed` / `auto·mixed` | hatched slider + dotted value box, two inks (§6); the aria-labels keep the words |
| automation glyphs `∿ ╱ ⟳` in the name | retained in the row's accessible name and as a small glyph next to the name inside the slider |
| checkbox for int 0/1 | latching button (`aria-pressed`), flashing under a generator |
| CSS marker/fill animation machinery (`--auto-*` vars, loop easing, fade rAF) | unchanged; it now drives the custom slider's fill/marker instead of the native range track |

Implementation posture for the slider: keep the native `<input type=range>`
as the interactive element (drag, keyboard, takeover handlers all work
today) and restyle it — `appearance:none` track/thumb with the fill, hatch,
marker, and name rendered by the existing wrapper (`.live-param-range-wrap`)
so no pointer/ARIA behavior is rewritten. The prototype's static markup is
the visual spec, not the DOM spec.

State keys (`openDrawers`, `drafts`, `automationAnchors`), the send/takeover
paths, and the host context contract (`getState`, `send`, `sendAutomation`,
`setInteracting`, `requestRender`) are unchanged. Hosts need no API
migration; the Device tab and Control tab get the new chrome by shipping the
shared module + CSS.

## 4. Proposed implementation split (children, in order)

1. **`3-tokens-and-chrome`** — land the new tokens (`--mod*`,
   `--value-fill`, `--hatch`, radii, focus rules) scoped to the control
   surface; light-pastel base repaint **only inside the panel** for now.
   Restyle buttons momentary/toggle, ∿ icon, drawer/tab chrome. No DOM
   changes. Verify: existing living journeys stay green;
   before/after screenshots.
2. **`4-row-regrind`** — the row grid (value box / name-in-slider / ∿),
   restyled range input with fill+marker, mixed hatching, drawer tabs.
   Retire the `value ▸ gen` switch. Update the affected living tests
   (`tests/verify_device_control_modes.py` and friends) in the same stitch.
3. **`5-hierarchy-and-persistence`** — accordion chrome per §9, collapsed
   state persistence.
4. **`6-non-float-kinds`** — toggle-button rendering (flash under
   generator), integer stepping, enum select (behind Q2's answer), event
   row rendering disabled pending 44.
5. **`7-preset-slot`** — the provisional preset row, disabled, with the
   patch name live. (One afternoon; exists so 41 slots in.)

Each child is independently shippable; the panel keeps working between
children (constraint honored). The app-wide repaint (bg outside the panel,
Show tab, rosters, Monitor) is **not** here — that's
`02-app-wide-rollout-design`.

## 5. Verification

- Extend the nearest living journeys under `tests/` (browser suite):
  row renders full manifest, drawer opens per kind, takeover unifies a
  mixed row, marker/fill reflect a running LFO (pixel-sample with Pillow
  where DOM can't see paint, per the §11 gotcha in CLAUDE.md).
- `tools/run-tests.sh browser` is the pre-tie gate per stitch.
- Real-hardware adoption check (Finn Jet + Ciro Toast) after child 2 and
  child 4: drag latency and takeover feel are judgment calls, flagged for
  Bob rather than claimed verified.

## 6. Open questions — all ruled by Bob, 2026-07-27

- **Q1 — cyan number boxes:** cyan **only under generators**. The
  modulation reservation wins over PD number-box congruence.
- **Q2 — enum automation:** enums **automate like ints** (generators emit
  integer indices; same quantization path as integer params).
- **Q3 — light-mode cyan:** current `#0798BC` accepted as is; no token
  split.
- **Q4 — takeover announcement:** stays as is — the status output line
  remains the announcement path.

## 7. Ratified in-session (2026-07-27, recorded so the tie is auditable)

- Pink/purple + cyan foundational palette; electric cyan; saturated pink
  light base; purple focus ring; no off-book colors.
- One hatch pattern, two inks; hatched value boxes with dots.
- Marker line on every slider, both inks.
- Label conventions (name inside control; sub-element labels left).
- `free` below `curve`, above the duration unit; full-width arg boxes.
- Momentary = rounded (PD bang), latching = sharp (PD toggle), ∿ circle
  exempt.
- Event row: three boxes + sync/send, boxes 58px min.
- 58px is the standardized number-box width across the surface.
- Integer number boxes right-align; floats left-align.
- Momentary radius softened to 7px (rounded, not a full pill).
