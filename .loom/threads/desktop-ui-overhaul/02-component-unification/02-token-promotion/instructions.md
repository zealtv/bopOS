# 02-token-promotion

Make the ratified control-panel token layer the app's token layer.

`dashboard/static/css/control-panel.css` binds `--cp-*` under exactly two
selectors (`.live-card`, `.device-control`) — correct scope discipline for
`01-control-panel`, and now the thing to widen. `style.css` carries a parallel
`--chrome-*` layer at 32px controls / 12px gaps and pads. No file uses both
(verified: 10 `--chrome-*` hits in `style.css`, 0 in `control-panel.css`;
30 `--row-h`/`--gap` hits in `control-panel.css`, 0 in `style.css`).

Work:

- Promote the metric and palette tokens to `:root`, mapping `--chrome-radius-*`
  onto `--radius-*` (both spellings already coexist by design).
- Retire `--chrome-control-height` / `--chrome-control-pad` / `--chrome-gap` /
  `--chrome-panel-pad` in favour of `--row-h` / `--gap` and the design's
  padding rules. Expect a real density drop app-wide; that is the point.
- ~~Reconcile the light theme.~~ **DONE 2026-07-30, ahead of this stitch.**
  Bob ratified the app-wide light repaint and then corrected it: *"the pink is
  a little heavy on the control panel — notice how it's used in the Excalidraw
  mockup. It's a background that panels sit on, not the colour of panels
  themselves."* Sampled from `mockup.png`, the light scheme is a **neutral grey
  scale on a pale pink ground**: ground `#f8f0fc`, panel `#f8f9fa`, subpanel and
  manual fill `#e9ecef`, inputs/buttons `#ffffff`, ink `#212529`. That is now
  the `--cp-*` light column, and `style.css`'s app-wide light `--bg` matches the
  ground. `--cp-bg` is the ONLY pink token — hold that line as the tokens widen:
  a pink panel is a regression, not a preference.

  One measured delta deliberately left open: the mockup's cyan fill is `#99e9f2`,
  more saturated than `--mod-fill` `rgba(7,152,188,.20)` renders over white. The
  cyan was ratified 2026-07-27 and Bob raised no objection, so changing it needs
  his say-so.
- `--mod*`, `--value-fill`, `--hatch` name inks, not surfaces; they are
  already global and need no change.
- Status colours (green/amber/red) stay reserved for connectivity, warnings and
  errors per `design-language.md` §11. Show message pills keep their ratified
  eight-colour semantic set (`25-message-pill-encoding`) and are not repainted.

Known off-palette surfaces to sweep, found while shooting the 2026-07-30
evidence: `#editor-panel` paints a teal `--feature`/`--feature-line` gradient,
which `design-language.md` §1 forbids (pink/purple + cyan only; status hues are
for status semantics). Header/tab chrome is still on `--chrome-*` 32px metrics
and reads visibly bloated beside the 24px panel — that contrast is the clearest
argument for this stitch and worth capturing in the before/after.

Verify with before/after screenshots of every tab at 1280 and 1680, light and
dark, retained in the stitch. A working harness is this stitch's `shoot.py`,
with its pre-change output kept as `baseline-2026-07-30-*.png` (the archived `.loom/tied/3-tokens-and-chrome/shoot_control_panel.py`
has rotted — it waits on a control-tab iframe selector that no longer resolves). `tools/run-tests.sh browser` must not regress
beyond the two known-red tests.
