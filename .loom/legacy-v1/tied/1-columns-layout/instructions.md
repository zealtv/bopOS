# 1-columns-layout

Make the Control tab hold N columns. Layout, add/remove, per-column state, and
the multi-column browser journey — **not** capture (`2`) and not the chrome
demotions (`3`).

Authority is `.loom/tied/1-columns-design/decisions.md`, then `proposal.md`,
then `judgment.md`. The mockups in that stitch are the visual target and
`mockup.py` regenerates them against the real app. Read the parent
`4-n-columns/instructions.md` first for what the three siblings share.

`3-iframe-retirement` left the column mounted at `#control-column-host` in
`index.html`, building its own DOM with no ids inside it, so this stitch adds a
column by adding a mount point.

## Columns

- **Fixed 342px** = 320px generator face + 2 × `--pad-panel` + 2 × 1px border.
  Never resizable, never elastic. Adding a column must move no existing control,
  which is why the width is fixed and the row is **left-aligned** — do not
  centre it.
- **Drop `max-width:1400px`** on this tab (`style.css`, `.tab-panel`). Measured
  at 342 + 12px gutter: 1280 → 3 columns, 1680 → 4, 2560 → 7. No count cap;
  make `+ column` quieter than `capture` instead.
- **Overflow scrolls horizontally, intact** — `06`'s ratified rule one level up.
  Never reflow, never auto-collapse into rails.
- **Each column scrolls its own body under a sticky header.** A page-level
  scroll would drag column 1 off screen while reaching column 4, and a column
  whose target label has scrolled away is a mis-target waiting to happen.
- **The column IS the card** — already true as of `3`: `.control-column` in
  `css/control-column.css` carries `--panel`, and `control-panel.css` §18 makes
  `.live-card` flat with a `--group-line` rule between consecutive cards. So a
  mixture already renders as ruled sections rather than nested boxes. Check it
  against `mockup-2560-*.png` rather than rebuilding it.
- **The sticky header is the column's own `TargetPicker`, `defaultOpen: false`.**
  Its terse readout (`all`, `Left+7`) is the column's title. An open picker
  costs ~180px of a 342px column, times N, for a control set once. The head
  element exists (`.control-column-head`); it needs the grip, the `✕`, and
  sticky positioning.
- Add/remove: `+ column` in a new thin tab strip, `✕` in the column header.
  Minimum one — at N=1 the `✕` is `visibility:hidden` rather than removed, so
  the header does not reflow when a second column appears.
- **The tab strip is created here** even though its right-hand action belongs to
  `2`: `+ column` on the left, and a placeholder slot on the right that `2`
  fills with `capture step · 12/16`. Say so in a comment so `2` does not have to
  guess whether the slot is deliberate.

## Targets — D5, D6, D7

- **A column that loses its target goes inert, never widens.** Already shipped
  by `0-prune-fallback-safety` and guarded in `verify_control_tab.py`; what is
  new here is that it must hold **per column**, keeping that column's slot and
  dead selector while its neighbours carry on.
- **An emptied group keeps its column**, rows disabled, meta `g3 · 0 Seats`,
  plus `aria-disabled` so the state is announced rather than inferred from a
  count in a `<small>`. See the fifth column in `mockup-2560-*.png`.
- **Overlapping columns get nothing** — no dedupe, no primary column, no
  warning. Overlap is the console idiom and the only place the system shows its
  aggregation rule working. Keep `presetReport()`'s exact member-set predicate
  (`control-column.js`); do **not** loosen it to "overlaps", or an apply in one
  column prints its report inside another.
- **`mixed` carries its content** — `dusk +2` rather than the bare word, so an
  All column beside a group column stops reading as a contradiction.
- **No ambient focus-seat follow** — done in `3`; `followFocusSeat` is already
  off the Control picker and `verify_control_tab.py` asserts the absence. What
  is owed here is the replacement: an explicit **"Open in Control"** action in
  the Seats inspector that focuses an existing column already targeting that
  seat if there is one, else appends one, then switches tabs.

## State — D9

One `bopos.control.columns` key holding an ordered list of
`{id, target, open}`, with **minted ids, never indices** — indices renumber on
remove and would silently re-point both storage and `aria-labelledby` at the
wrong column. Migrate `bopos.target.control` once into column 1.
`bopos.control.collapsed-branches` stays **global** across columns: the operator
is pruning the manifest, not a card.

Duplicate-target columns are **legal**; do not prevent them.

## Watch for

- Gotcha 17 at full strength — with N columns every component class resolves N
  times. **No `id` attribute anywhere inside a column** (`3` already removed the
  three that were there); scope every selector to the column root; give each
  column's picker a minted `data-target-picker` id.
  `data-live-scope`/`data-live-id` are *target* identifiers and are correctly
  non-unique — never select on them alone.
- **One live region per column, not per card**, and prefix the message with the
  column's target (*"Left: gain automation stopped, set to 0.4"*). `3` gave the
  column a single `.control-column-status`, but `liveCard` still emits a
  per-card `.live-param-status`; two columns showing Seat 3 would announce twice
  with no way to tell which acted.
- Columns are labelled `<section>`s pointing at their own header, so region
  navigation reads `all`, `Left`, `Seat 7`. **No positive `tabindex`** — DOM
  order is already the correct reading order; put the picker and `✕` first
  within the column so an operator can reach the next column's target without
  traversing forty parameter rows.
- `✕` and `+ column` are momentary, so they must **not** carry `aria-pressed`,
  or design-language §8 gives them the latching square radius.
- `.control-column*` is already registered in
  `tests/test_css_component_ownership.py`'s `COMPONENTS` map (`3`). Add the
  third selector to `control-panel.css` §3's panel token binding **only if** the
  column becomes a token host.
- **Add CLAUDE.md gotcha 19** when this lands: *a target identifier is not an
  element identifier* — the successor to gotchas 12 and 17.

## Verify

`tools/run-tests.sh fast` and `browser`. Extend `tests/verify_control_tab.py`
with a multi-column journey: add a column, give the two columns different
targets, confirm a send from one does not move the other's cards, remove a
column, reload and confirm the layout came back. Add the D5 case explicitly at
N>1 — delete a targeted seat and assert that column goes inert while its
neighbour is untouched, because that is the regression that would be silent and
dangerous. The `about:blank` / `localStorage` trap is gotcha 18;
`tests/verify_target_picker.py` is the worked example of testing persistence
with `page.route` on a fabricated origin.

Screenshots at 1280/1680/2560 against the ratified mockups.
`.loom/tied/3-iframe-retirement/shoot.py` is the current working harness (and
writes `bopos-theme`, not the `bopos.theme` bug `02-token-promotion` recorded).
