# 02-token-promotion — decisions

2026-07-30. The ratified control-panel metric layer is now the app's metric
layer, and the parallel `--chrome-*` layer is gone.

## What the promotion actually was

The metric tokens (`--row-h`, `--gap`, `--radius-*`) were already declared at
`:root` in `control-panel.css`; only the *palette* was scoped to `.live-card` /
`.device-control`. So promotion was not a move — it was **deleting the rival
layer and repointing its 83 consumers**:

| retired | promoted to | value change |
|---|---|---|
| `--chrome-radius-panel` | `--radius-panel` | none (6px) |
| `--chrome-radius-control` | `--radius-control` | none (4px) |
| `--chrome-radius-small` | `--radius-small` | none (3px) |
| `--chrome-control-height` | `--row-h` | **32px → 24px** |
| `--chrome-gap` | `--gap` | **12px → 6px** |
| `--chrome-control-pad` | `--pad-control` | **4px 8px → 2px 6px** |
| `--chrome-panel-pad` | `--pad-panel` | **12px → 10px** |

`--pad-control` and `--pad-panel` are new names, not a new layer: the retired
tokens had 17 consumers between them and `design-language.md` §4 has no padding
token (panel rows get their height from `--row-h` and need none). They are
declared in the promoted `:root` block beside the metrics they belong with, and
`--pad-control` is expressed as `2px var(--gap)` so it tracks the rhythm rather
than restating it.

## Three decisions worth recording

1. **The metric block stays in `control-panel.css`.** It looks like it belongs
   in `style.css` now that it is app-wide, but `facilitator.html` loads
   `facilitator.css` + `control-panel.css` and **not** `style.css`. The tokens
   live in the one file both hosts load, which is the same reason the file
   exists at all. Its header comment now says so.

2. **`--header-h:40px` is a token, not a literal.** The header height had six
   literal `64px` sites — the flex header, the later grid header that overrides
   it, three responsive `min-height` floors, and `.layout`'s
   `calc(100vh - 64px)` — plus `.tab-stage`'s `calc(100vh - 115px)` and the
   Show inspector's `top:72px` / `calc(100vh - 90px)` derived from header + tab
   bar. Literals that must agree and cannot are how the two token layers
   happened; the derived offsets are now recomputed from the real bar heights
   (header 40 + tab bar 33 = 73).

3. **Only app-chrome *primitives* were retuned.** `header`, `.primary-tabs`,
   `.tab-panel`, `section`, `button`, `main`, `aside`, `#spatial-section`. The
   per-surface literals inside components (`18px` margins, `25px` tab
   headings, the facilitator's own target-filter chrome) were deliberately left
   alone: dead headings and toolbars are `03-chrome-reclamation`'s, the target
   filter is `07-target-selector-component`'s, and the Control tab's iframe —
   the reason its filter row still reads 48px tall beside a 24px panel — is
   `08-control-tab-columns`'. Poaching them here would have made this diff
   unreviewable and their stitches ambiguous.

## Two off-palette fixes the instructions flagged

- **`#editor-panel`'s teal gradient is gone** —
  `linear-gradient(135deg,var(--feature),var(--panel) 55%)` with a
  `--feature-line` border, which `design-language.md` §1 forbids (pink/purple +
  cyan only; status hues for status). It is now flat `--panel` with a
  `--group-line` border. Its three fellow `--feature-line` consumers
  (`#fleet-patch-panel`, `#group-map-bar`, `.group-detail`) moved to
  `--group-line` too, which left `--feature` and `--feature-line` with **zero
  consumers**, so both declarations are deleted from `style.css` and
  `facilitator.css`. Dark `#3d5869` was the only genuinely off-hue line token
  in the app.

- **The pink ground is now one value everywhere.** The 2026-07-30 repaint set
  `--bg:#f8f0fc` in `style.css`'s `@media (prefers-color-scheme: light)` block
  but missed `:root[data-theme="light"]`, so the *explicit* light theme kept the
  old lavender `#f4f1f8` — the theme toggle and the OS preference disagreed
  about the ground, and `--cp-bg` (the panel's ground, `#f8f0fc`) matched
  neither. Both `style.css` light columns and both `facilitator.css` light
  columns now read `#f8f0fc`. This is finishing the ratified ground, not
  reopening it.

## Held, not touched

- **The app-wide light *panel* scale** is still the purple-tinted greys
  (`--panel:#fff`, `--surface-bar:#e9e4ef`, `--panel-soft:#f0edf4`), not the
  mockup's neutral `#f8f9fa`/`#e9ecef`. The instructions strike the light-theme
  reconciliation out as done ahead of this stitch, and Bob's correction was
  specifically *"the pink is a little heavy"* — the pink-panel regression, which
  is fixed. Repainting the app's greys neutral is a visible, Bob-facing change
  with no ruling behind it; it belongs to whichever stitch shows him the light
  app beside the mockup. Recorded here so it is a decision, not an oversight.
- **The cyan saturation delta** (`#99e9f2` in the mockup vs `--mod-fill`
  `rgba(7,152,188,.20)` over white) is still open and still needs Bob.
- **Show message pills** and the spatial map keep their ratified colours.
