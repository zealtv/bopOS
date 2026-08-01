# 3-tokens-and-chrome — decisions and evidence

Landed the ratified control-panel token layer and chrome with **no DOM
changes**. Authority: `design-language.md` + `control-panel-design.md` in the
tied `2-control-panel-design` stitch.

## What shipped

New file `dashboard/static/css/control-panel.css`, linked from **both**
`index.html` and `facilitator.html`.

1. **`--mod`, `--mod-fill`, `--mod-hatch`, `--mod-soft`, `--value-fill`,
   `--hatch`** — dark + light, per the design-language token table.
   `--mod-hatch`, `--value-fill` and `--hatch` are declared but not yet
   consumed: they are the mixed/manual fill inks that `4-row-regrind` paints
   onto the restyled slider.
2. **`--radius-momentary` (7px), `--radius-toggle` (1px)**, plus the design's
   `--radius-panel/control/small` names alongside the shipping
   `--chrome-radius-*` spellings.
3. **Light-theme base repaint** (saturated pink pastel) via `--cp-*` tokens
   rebound locally on the panel containers.
4. **Focus policy** — `accent-color: var(--accent)` and a purple
   `:focus-visible` outline on the surface; the cyan precision-readout focus
   ring from `40-precision-param-input` went purple with it.
5. **Button shapes** — momentary 7px, latching sharp keyed off
   `button[aria-pressed]`, pressed latch wearing `--mod-fill` / `--mod`.
   The ∿ icon's 18px-circle rule ships too (see below).

## Decisions taken in the work

**One shared stylesheet, not two edits.** The instruction says "add … to
`dashboard/static/css/style.css`", but the surface has two hosts and
`facilitator.css` already duplicates the drawer chrome with a comment
apologising for it. Token drift between the two files is exactly what this
layer exists to prevent, so the tokens went into a third file both pages
load. No existing rule changed; both stylesheets keep working untouched.

**The panel scope is `.live-card, .device-control`.** These are the two
containers that hold a `ControlSurface`. `.promoted-controls` alone would
have excluded the header and `send all` that design §1 counts as part of the
panel. The repaint therefore does reach the **standalone facilitator's**
cards, not just the embedded Control tab — palette is a different axis from
the tablet-first layout constraints the standalone keeps, and holding the two
views to different colours would be worse than holding them to one. Flagged
for Bob as the one judgment call here.

**Dark is a no-op by construction.** The design's dark panel values are
byte-identical to the shipping dark tokens, so `--cp-*` in dark just restates
them. Every dark difference in the screenshots comes from a chrome rule, not
the repaint — which keeps the blast radius of this stitch small and legible.

**Three inks corrected as off-book palette, beyond the literal brief:**

- the native range track was `--accent-cyan` and the facilitator's 0/1
  checkbox was `--accent-warm` (amber). Cyan is reserved for modulation and
  there is no third hue, so both take `--accent`. `4-row-regrind` replaces
  the native track with the `--value-fill` fill + marker; the accent stands
  in until then.
- the value readout was cyan on every row. Per Q1, cyan means a generator, so
  the readout is `--text` normally and `--mod` under `.automated`.
- the facilitator's text param drew its field from `--bg`, which is now the
  saturated page pink. A value box is `--input`.

**`--auto` is rebound to `--mod` inside the panel.** `--auto` is the shipping
automation ink (markers, glyphs, generator preview trace). Inside the control
surface it *is* the modulation ink, so pointing it at `--mod` moved the whole
existing automation machinery onto the ratified cyan without touching a
single automation rule.

**The ∿ icon rule ships without its markup.** The brief lists "∿ icon
circular" but the element arrives with `4-row-regrind`, which retires the
`value ▸ gen` switch. The `.live-param-mod` rule (18px circle, idle `--dim`
on `--input`, active `--mod` ink / `--mod-soft` face) lands here with the
rest of the button vocabulary so stitch 4 only has to emit the element. If
stitch 4 wants a different class name, rename in one place.

**Type is untouched.** Design-language §3 (monospace everywhere, 12px base)
is real but it is a re-layout, not a token: it belongs with `4-row-regrind`
and `02-app-wide-rollout-design`, not in a no-DOM-changes chrome slice.

## Verification

- `tools/run-tests.sh browser` — **12/12 PASS** (full summary; no journey
  needed editing, which is the point of a no-DOM-changes slice).
- `tools/run-tests.sh fast` — 182 tests, **1 failure**:
  `test_device_control_routing.
  test_reappearing_physical_device_replays_persistent_enabled_state`.
  **Pre-existing**: it fails identically on clean `main` with this stitch
  stashed. Untouched by CSS; not diagnosed here.
- `before-*.png` / `after-*.png`: Control tab and Device-tab panel, dark and
  light, plus a Control tab with a generator drawer open. (Flat filenames
  rather than `before/` and `after/` directories — loom reads a subdirectory
  as a child stitch and refuses to tie the parent.) Generated by
  `shoot_control_panel.py <dir>` (real
  `dashboard/server.py` + `tools/simfleet.py` on free ports, headless
  Chromium), which is kept for the later children of this thread.

Not verified: real-hardware feel. This slice paints nothing that moves, so
the adoption check the design schedules after children 2 and 4 still stands
where it is.
