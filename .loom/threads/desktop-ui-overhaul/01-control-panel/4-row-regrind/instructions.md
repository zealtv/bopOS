# 4-row-regrind

Second slice of the ratified control-panel design (authority: the tied
`2-control-panel-design` stitch — `control-panel-design.md` §3 has the
mapping table).

Regrind the parameter row in `dashboard/static/js/control-surface.js` to
the ratified grammar `[58px value box][name-in-slider][∿ icon]`:

- Keep the native `<input type=range>` as the interactive element;
  `appearance:none` restyle with fill, marker line (both inks), and the
  name inside the trough. The existing `--auto-*` animation machinery and
  fade rAF drive the new fill/marker.
- Floats left-align in value boxes; integers right-align.
- Mixed states: one 45° slash pattern, `--hatch` ink for mixed values,
  `--mod-hatch` when a generator is involved; value box hatches with dots.
- Replace the `value ▸ gen` mode switch with the ∿ icon
  (open/close drawer; same `openDrawers` keying). Drawer kind select
  becomes the `LFO | loop | fade` tab row (same `GEN_KINDS`/compile path).
  Apply/Stop stay, momentary-shaped.
- Takeover announcement path unchanged (Q4 ruling).

Update the affected living journeys under `tests/` in the same stitch.
Verify: `tools/run-tests.sh browser`; flag drag/takeover feel for a
hardware adoption check (Finn Jet + Ciro Toast) rather than claiming it.
