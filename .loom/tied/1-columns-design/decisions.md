# Decisions — 08-control-tab-columns/1-columns-design

**The proposal is RATIFIED in full (Bob, 2026-07-31), with one amendment.**
Bob: *"i think never is fine. i read over the proposal and am happy with it."*

`proposal.md` is the design of record; `judgment.md` is the reasoning;
`ground-truth.md` is the code the reasoning stands on. This file records what
was ruled, and is authoritative where it differs from the proposal.

## The nine decisions, as ratified

| # | ruling | status |
|---|---|---|
| D1 | **Capture is venue-wide and takes no scope argument.** `scope`/`id` leave both capture verbs, `presetScope()` is deleted, `_capture_show_seats` collapses to every seat. Reachable as one unparameterised action from the Show edit bar (`✛ Capture`) and from one control in a new Control-tab strip. Never inside a column. | ratified as proposed |
| D2 | **No dialogs.** The two `alert()`s and the `confirm()` come out. Ambient count on the control → arm → non-modal preview of the messages the server would mint → commit → inline undo (~8s). "No show loaded" / "nothing applied" are disabled states with the reason in place. | ratified as proposed |
| D3 | **Captured steps get a derived name** (`dusk + bloom + solo`) instead of `"Captured presets"`, handed to the Show tab's existing click-to-edit rename. | ratified as proposed |
| D4 | **Columns are fixed 342px cards, left-aligned, `max-width:1400px` dropped on this tab.** Not resizable, not elastic. Overflow scrolls horizontally, intact. Each column scrolls its own body under a sticky header that is its own target picker, closed by default. The column *is* the card; per-target blocks are ruled sections. | ratified as proposed |
| D5 | **A column that loses its target goes inert, never widens to All.** `pruneFallback: "empty"` on `TargetPicker` for the Control host; Assets keeps advance-to-next-eligible. Emptied group (group exists, zero members) keeps its column, rows disabled, `aria-disabled`. | ratified as proposed |
| D6 | **Overlapping columns need nothing** — no dedupe, no primary column, no warning. Keep the apply report's exact member-set predicate. Adopt one win: `mixed` carries its content (`dusk +2`). | ratified as proposed |
| D7 | **No ambient focus-seat follow at all.** ~~Follow when exactly one column exists.~~ | **AMENDED — see below** |
| D8 | **Cut chrome from the Control column.** Device commands leave it (kept on Remote); `new`/`save`/`del` demote behind one disclosure with the `<select>` staying in the row; `Send all` moves to an overflow. | ratified as proposed — flagged as a behaviour change and ruled in; Bob confirmed the `Send all` demotion separately (*"demoting send all is fine too"*) |
| D9 | **One `bopos.control.columns` layout key** holding `{id, target, open}` with minted ids, never indices. `bopos.target.control` migrates once into column 1. `bopos.control.collapsed-branches` stays global. | ratified as proposed |

## D7 — amended

The proposal kept ambient follow as a compatibility kindness *when exactly one
column exists*, and flagged it as the ruling held most loosely. **Bob ruled
"never".**

So: `followFocusSeat` is **retired on the Control host outright**, at every N.
There is no residual single-column behaviour to preserve and no N-dependent
rule to implement — which is strictly simpler than what was proposed, and
removes the last piece of invisible state from the design.

The Seats → Control workflow that `37/10` preserved survives as the explicit
**"Open in Control"** action in the Seats inspector: focus an existing column
already targeting that seat if there is one, else append one, then switch tabs.

`bopos.selected-seat` remains the Seats tab's own selection key
(`target-picker.js:28`) and `07`'s ruling that it is one shared key is
untouched. Control simply stops reading it. The `followFocusSeat` option itself
stays on the component — it has no other consumer today, but removing it is a
component change with no benefit, and `adoptFocusSeat`'s "adopt when it moves,
not on load" rule is worth keeping documented for any future consumer.

## Also ruled

- **No lore item.** The whole artifact — brief, three consults, judgment,
  proposal, generator and mockups — travels with this stitch into `tied/`, which
  is where `automation-4-waveform-ux-gate` (the precedent this stitch was
  modelled on) also kept its consult set. A lore item would duplicate it.
- **The two sibling findings are carried into their own stitches**, not
  implemented here: the document-wide fade animator into
  `2-control-column-component`, and the card chrome that lives in
  `facilitator.css` into `3-iframe-retirement`.
- **D5 is pulled out as its own stitch, `0-prune-fallback-safety`.** It is a
  live defect at N=1 today, and `4-n-columns` sits behind `2` and `3`, so
  shipping the fix inside `4` would leave a silent target-widening bug in the
  live surface for the whole duration of the thread. The `0-` prefix sorts it
  first; **Bob may reorder it — it is a queue-order call, and it was taken by
  the agent rather than ratified.**

## Not in scope, recorded for their own sake

Two findings from the consult that the design does not act on:

- **The guarding is inverted.** Capture (silent, reversible) had three dialogs;
  applying a preset (instantly audible across a whole target, provenance
  overwritten, no undo) is a bare `<select>` `onchange`
  (`control-surface.js:413-418`). D2 fixes the over-guarded half. Nobody asked
  for a confirm on apply — a modal in the audio path is worse than the mistake —
  but the asymmetry is on the record.
- **Restart amnesia.** `applied_preset`/`preset_dirty` are stripped before
  persistence (`state.py:420-427`) while seat params are not, so after a
  dashboard restart the venue sounds identical but captures nothing. This is
  ratified F4 behaviour and stays. D2's empty state must say *why* it is empty —
  a different sentence for a different cause.
