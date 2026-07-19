# 15-show-polish — Show tab polish + Patch tab tidy

Bob's 2026-07-19 braindump (verbatim in lore item
`2026-07-19-show-tab-polish-braindump`) after operating the completed
`14-show-tab` slice. This thread is the decomposition, ordered in sequence
of attack: bugs first, then engine semantics, then transport/cue policy,
then layout, then interaction, then the Patch tab, then docs. It continues
the accepted sweep numbering after `14-show-tab` and takes priority over
`patch-workflow-friction` until tied.

## Standing rulings from the braindump (fixed for this thread)

- **Exclusive playback:** only one step may play at a time (single column;
  the data model stays multi-column-agnostic but the engine enforces one
  playing step).
- **All cues forward-sync by design.** The per-step `forward_sync` flag and
  its tick box are retired; a global cue lead-time control replaces the
  hard-coded 500 ms. Old show files carrying `forward_sync` must still load.
- **Message editing goes keyboard + drag.** Cut/copy are keyboard-only;
  rearranging is click-and-drag (within and between steps); the
  cut/copy/move buttons leave the edit section; keyboard delete stays;
  keyboard undo is required. Steps and dividers also reorder by drag.
- **Patch tab:** "facilitator" renames to "Dashboard" — a **full rename**,
  ratified by Bob 2026-07-19: the manifest key becomes `dashboard` (legacy
  `facilitator` accepted on load, normalized on save; contract §8 gets the
  amendment line). The legacy presentation-only `group` manifest field is
  removed (nothing in the demo patches uses it) and demo manifests tidied;
  the path field's example hint must read unambiguously as an example.

## House rules that bite here

- Amending tied verifies from `14-show-tab` is expected as the UI moves —
  log every amendment in the stitch worklog, per the 5b/5c precedent.
- `.pd` files are Bob's. p7's manifest tidy is JSON-only; if a demo tidy
  would require touching PD routes, mark `.waiting` and surface it.
- Playwright verifies: house pattern (`~/.venvs/bopos` venv, simfleet on
  random ports, repo by marker, type-aware dialog handler).

## Stitch order (sequence of attack)

1. `p1-zero-value-and-transport-bugs` — the two operator-facing bugs:
   param values can't be set to 0, and transport clicks lost during the
   round-trip window (includes the next-glyph legibility and title-shift
   annoyances in the same territory).
2. `p2-exclusive-playback-and-progress` — one-playing-step engine rule,
   progress-meter fill, armed blink-pulse.
3. `p3-global-transport-and-cue-lead` — global transport strip controls,
   forward-sync retirement, global cue lead time.
4. `p4-step-list-scrollbox` — resizable step-list scroll box, stable add
   bar, console default heights.
5. `p5-inspector-defaults` — then-actions default single stop row
   (non-deletable), collapsible message target section.
6. `p6-drag-and-keyboard-editing` — drag/keyboard/undo editing model
   (split if it fights back).
7. `p7-patch-tab-tidy` — Dashboard rename, legacy group removal, path
   hint.
8. `p8-docs-and-handoff` — docs sweep, CLAUDE.md ordering, handoff.
