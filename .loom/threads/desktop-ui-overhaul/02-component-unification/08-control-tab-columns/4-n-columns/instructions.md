# 4-n-columns

Ship the N-column Control tab to the design ratified in `1-columns-design`.

**Unblocked 2026-07-31** — Bob ratified `1` in full, amending D7 to "never".
The authority is `.loom/tied/1-columns-design/decisions.md`, then `proposal.md`
beside it, then `judgment.md` for the reasoning. The mockups in that stitch
(`mockup-1280/1680/2560/760/armed-*.png`) are the visual target, and
`mockup.py` regenerates them against the real app.

Needs `2` and `3` done: `2` makes a column instantiable, `3` puts it in a
document that can hold more than one.

## The ratified design, as build instructions

### Columns

- **Fixed 342px** = 320px generator face + 2 × `--pad-panel` + 2 × 1px border.
  Never resizable, never elastic. Adding a column must move no existing control,
  which is why the width is fixed and the row is **left-aligned** — do not
  centre it.
- **Drop `max-width:1400px`** on this tab (`style.css:44`, `.tab-panel`).
  Measured at 342 + 12px gutter: 1280 → 3 columns, 1680 → 4, 2560 → 7. No count
  cap; make `+ column` quieter than `capture` instead.
- **Overflow scrolls horizontally, intact** — `06`'s ratified rule one level up.
  Never reflow, never auto-collapse into rails.
- **Each column scrolls its own body under a sticky header.** A page-level
  scroll would drag column 1 off screen while reaching column 4, and a column
  whose target label has scrolled away is a mis-target waiting to happen.
- **The column IS the card.** It carries `--panel`; a mixture renders per-target
  **ruled sections**, not nested bordered boxes — §12 forbids both nesting cards
  and showing ground inside a card's footprint. `liveCard`'s `<article>` loses
  its border, radius and background inside a column and keeps its header line.
- **The sticky header is the column's own `TargetPicker`, `defaultOpen: false`.**
  Its terse readout (`all`, `Left+7`) is the column's title. An open picker
  costs ~180px of a 342px column, times N, for a control set once.
- Add/remove: `+ column` in the tab strip (below), `✕` in the column header.
  Minimum one — at N=1 the `✕` is `visibility:hidden` rather than removed, so
  the header does not reflow when a second column appears.

### Capture-as-step — D1, D2, D3

The consult's headline, and the biggest single change here:

- **Capture is venue-wide and takes no scope argument.** Delete `scope`/`id`
  from `preview_show_preset_capture` and `capture_show_preset_step`; delete
  `presetScope()` (`facilitator.js:381-397`); collapse `_capture_show_seats`
  (`server.py:1804-1812`) to `list(self.state.seats.values())`. This is a
  **removal** — the arrangement was never carried by the scope, it is rebuilt
  from per-seat `applied_preset` by `_captured_show_preset_messages`.
- **One affordance per surface, never inside a column.** A new thin Control-tab
  strip carries `+ column` (left) and `capture step · 12/16` (right), and the
  Show tab's edit bar gains `✛ Capture` beside `✛ Step` — same words, same
  unparameterised behaviour.
- **No dialogs.** The two `alert()`s and the `confirm()`
  (`facilitator.js:247-265`) come out. Ambient count → click **arms** → non-modal
  preview listing the messages the server would mint → commit → `captured "…" ·
  undo` in the same slot for ~8s. See `mockup-armed-dark.png`.
- The preview marks **dirty** rows ("captures the preset, not the edits") and
  **site-bound** seat-id targets vs portable `group:<name>` ones — both ratified
  behaviour that nothing currently says out loud.
- **The round trip can go.** The client already holds `applied_preset` on every
  seat (it is what `presetProvenance()` reads, `control-surface.js:277-286`) and
  after `3` this document receives `show`/`shows` (`server.py:289-292`), so the
  count and the show-loaded check are both local. `preview_show_preset_capture`
  existed only because the iframe could see neither.
- **Disabled states, not alerts**: no show loaded, and nothing applied. The
  nothing-applied case must distinguish its causes — after a dashboard restart
  the venue sounds identical but provenance is gone (`state.py:420-427`), and
  the operator needs a different sentence for that than for "nothing has been
  applied yet".
- **Name the step.** Derive the alias from content (`dusk + bloom + solo`)
  instead of `"Captured presets"` (`show_model.py:859`, never overridden) and
  hand the new step to the Show tab's click-to-edit rename (`show.js:95-111`).
- **Undo** sends the existing `undo_show`. It undoes the *last show mutation*,
  whatever it was — so either clear the affordance on any intervening show
  mutation or check the top of the undo stack before firing.

### Targets — D5, D6, D7

- **A column that loses its target goes inert, never widens.** `0-prune-fallback-safety`
  ships the component option; if that stitch has not landed when you get here,
  do it first — it is a live defect, not a column feature. The column keeps its
  slot and dead selector and renders `Seat 7 is no longer in this venue` with a
  re-target action and **no controls at all**.
- **An emptied group keeps its column**, rows disabled, meta `g3 · 0 Seats`,
  plus `aria-disabled` so the state is announced rather than inferred from a
  count in a `<small>`. See the fifth column in `mockup-2560-*.png`.
- **Overlapping columns get nothing** — no dedupe, no primary column, no
  warning. Overlap is the console idiom and is the only place the system shows
  its aggregation rule working. Keep `presetReport()`'s exact member-set
  predicate (`facilitator.js:70-79`); do **not** loosen it to "overlaps", or an
  apply in one column prints its report inside another.
- **`mixed` carries its content** — `dusk +2` rather than the bare word, so an
  All column beside a group column stops reading as a contradiction.
- **No ambient focus-seat follow, at any N** (D7 as amended by Bob). Drop
  `followFocusSeat` from the Control picker. The Seats → Control workflow returns
  as an explicit **"Open in Control"** action in the Seats inspector: focus an
  existing column already targeting that seat if there is one, else append one,
  then switch tabs.

### Chrome — D8 (behaviour change, ruled in by Bob)

Six chrome controls per seat card × three cards per mixture × three columns is
fifty-four controls before the operator reaches a parameter.

1. **Device commands leave the Control column** — Update bopOS / Reboot /
   Shutdown (`facilitator.js:172-178`). **They stay on Remote.** The Devices tab
   owns device lifecycle; `07`'s "Set patch…" hand-off is the pattern.
2. **`new`/`save`/`del` demote behind one disclosure**, `<select>` stays in the
   row. Note `del` is **patch-scoped** — it removes the preset from the store
   for the whole installation (`control-surface.js:425`) while sitting in a row
   whose every other control is target-scoped.
3. **`Send all` moves to an overflow** (`facilitator.js:168-170`) — a rescue
   action for a returning node, not a live gesture. Confirmed by Bob separately.

### State — D9

One `bopos.control.columns` key holding an ordered list of
`{id, target, open}`, with **minted ids, never indices** — indices renumber on
remove and would silently re-point both storage and `aria-labelledby` at the
wrong column. Migrate `bopos.target.control` once into column 1.
`bopos.control.collapsed-branches` stays **global** across columns: the operator
is pruning the manifest, not a card.

Duplicate-target columns are **legal**; do not prevent them.

## Watch for

- Gotcha 17 at full strength — with N columns every component class resolves N
  times. **No `id` attribute anywhere inside a column**; scope every selector to
  the column root; give each column's picker a minted `data-target-picker` id.
  `data-live-scope`/`data-live-id` are *target* identifiers and are correctly
  non-unique — never select on them alone.
- **One live region per column, not per card**, and prefix the message with the
  column's target (*"Left: gain automation stopped, set to 0.4"*). Two columns
  showing seat 3 currently emit the same announcement twice from two regions
  with no way to tell which acted (`facilitator.js:208`).
- Columns are labelled `<section>`s pointing at their own header, so region
  navigation reads `all`, `Left`, `Seat 7`. **No positive `tabindex`** — DOM
  order is already the correct reading order; put the picker and `✕` first
  within the column so an operator can reach the next column's target without
  traversing forty parameter rows.
- `✕` and `+ column` are momentary, so they must **not** carry `aria-pressed`,
  or design-language §8 gives them the latching square radius.
- Register `.control-column-*` in `tests/test_css_component_ownership.py`'s
  `COMPONENTS` map, and add the third selector to `control-panel.css:122`'s
  panel token binding if the column becomes a token host.
- **Add CLAUDE.md gotcha 19** when this lands: *a target identifier is not an
  element identifier* — the successor to gotchas 12 and 17.

## Verify

`tools/run-tests.sh fast` and `browser`. Extend `tests/verify_control_tab.py`
with a multi-column journey: add a column, give the two columns different
targets, confirm a send from one does not move the other's cards, remove a
column, reload and confirm the layout came back. Add the D5 case explicitly —
delete a targeted seat and assert the column goes inert rather than becoming an
All column, because that is the regression that would be silent and dangerous.
The `about:blank` / `localStorage` trap is gotcha 18;
`tests/verify_target_picker.py` is the worked example of testing persistence
with `page.route` on a fabricated origin.

Screenshots at 1280/1680/2560 against the ratified mockups.
