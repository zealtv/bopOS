# 4-n-columns

Ship the N-column Control tab to the design ratified in `1-columns-design`.

**Unblocked 2026-07-31** — Bob ratified `1` in full, amending D7 to "never".
`2-control-column-component` made a column instantiable and
`3-iframe-retirement` put it in a document that can hold more than one.

**Split into three on 2026-07-31.** As one stitch this bundled a layout change,
a cross-file backend removal, a shared-component behaviour change, and a test
migration — the same four-way shape that got the parent
`08-control-tab-columns` split in the first place. Work them in name order:

1. **`1-columns-layout`** — the columns themselves: fixed 342px track, the tab
   strip, add/remove, per-column scroll and target state, `bopos.control.columns`,
   the "Open in Control" replacement for the retired focus-seat follow, and the
   multi-column browser journey. First because the tab strip that `2` needs is
   created here.
2. **`2-venue-wide-capture`** — D1–D3. Capture takes no scope argument, the
   server round trip goes away, and three dialogs become arm → preview →
   commit → undo. Independent of column count; second only because its
   affordance needs `1`'s strip to sit in.
3. **`3-chrome-demotions`** — D8. Device commands, the preset actions and
   `Send all` leave the Control card. Last of the three because they change the
   **shared** `ControlSurface`, which is better done once the layout has
   stopped moving.

**A fourth child was added on 2026-07-31** (Bob), after the three above:
`4-current-show-broadcast`. It is not column work — `2-venue-wide-capture`
found that `set_current_show` never rebroadcasts `state`, and with no periodic
full-state broadcast anywhere the Monitor System panel reads `none loaded`
while a show is loaded. Bob queued it here rather than as a peer of `09`/`11`;
the stitch's own instructions record that this is an ordering call and where to
lift it to if it ever holds the thread open.

## Shared authority

`.loom/tied/1-columns-design/decisions.md` is the ruling, `proposal.md` beside
it the detail, `judgment.md` the reasoning. The mockups in that stitch
(`mockup-1280/1680/2560/760/armed-*.png`) are the visual target, and `mockup.py`
regenerates them against the real app.

`.loom/tied/3-iframe-retirement/decisions.md` says what the columns are being
built on: the column owns its markup and addresses nothing inside itself by id,
`.control-column` is the card and `.live-card` is already flat (D1, adopted
early), and `control-panel.css` §18 vs `css/control-column.css` is the
ownership split — the card face belongs to the control panel, the shell to the
column, and `tests/test_css_component_ownership.py` enforces it.

## Ties when

All four children are tied and the tab matches the ratified mockups at
1280/1680/2560. `08-control-tab-columns` has no other children, so tying this
ties the thread. The mockup match is the test for `1`–`3` only;
`4-current-show-broadcast` is judged by the Monitor panel telling the truth.
