# 4-n-columns

Ship the N-column Control tab to the design ratified in `1-columns-design`.

**`.waiting` on that ratification** — not on a person's availability, on the
document. Claim this stitch when `1` is tied and its `decisions.md` exists.
Needs `2` and `3` done too: `2` makes a column instantiable, `3` puts it in a
document that can hold more than one.

## Scope

- Add and remove a column. **Minimum one** — the tab is never empty (Bob).
- Each column carries its own `TargetPicker`, targeting all / a selection of
  groups / a selection of seats / a mixture. Per-column storage key, per `07`'s
  per-host precedent and whatever `1` rules for `followFocusSeat`.
- Column layout persists in `localStorage` (Bob), keyed like
  `bopos.control.collapsed-branches` and `bopos.device-control-open`.
- Column widths, the no-seats state, the overlapping applied-preset marker, and
  capture-as-step ownership: **as ratified in `1`**. Do not re-decide them here.
- **§12 — columns are cards on the ground.** The gutter between them is the
  only place `--bg` shows. `3` deleted the iframe's
  `background:var(--bg)`; do not reintroduce it on the column container.

## Watch for

- Gotcha 17 at full strength — with N columns every component class resolves N
  times. Scope to the column root, and prefer per-column data attributes to
  ids.
- Anything `2` left as page-level that turns out to be per-column once there
  are two of them. The preset apply report is the likely one:
  `presetReport()` (`facilitator.js:70-79`) matches a broadcast report to a row
  by exact target-set equality, and two columns can both match.

## Verify

`tools/run-tests.sh fast` and `browser`. Extend `tests/verify_control_tab.py`
with a multi-column journey: add a column, give the two columns different
targets, confirm a send from one does not move the other's cards, remove a
column, reload and confirm the layout came back. The `about:blank` /
`localStorage` trap is gotcha 18 — `tests/verify_target_picker.py` is the
worked example of testing persistence with `page.route` on a fabricated origin.

Screenshots at 1280/1680/2560 against the ratified mockups.
