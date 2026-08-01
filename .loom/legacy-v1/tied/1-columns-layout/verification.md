# Verification — 4-n-columns/1-columns-layout

## Automated

- `tools/run-tests.sh fast` — 255 tests, OK. Includes
  `tests/test_css_component_ownership.py`, which the new `style.css` rules pass
  because the tab places columns with `flex` (positioning) and paints nothing
  on them.
- `tools/run-tests.sh browser` — all 20 journeys pass.
- `tests/verify_control_tab.py` grew the multi-column journey the stitch owes,
  17 new checks: stored layout restored; the sole column's picker closed and
  serving as its title; ✕ hidden at N=1 and offered at N=2; a new column
  arriving open to be aimed; two columns carrying different targets with
  distinct minted picker ids; a send in one column leaving the other's cards
  byte-identical; one live region per column and none per card; a real reload
  restoring the layout with minted ids; Open in Control appending a column and,
  asked twice, focusing rather than duplicating; **D5 at N>1** — deleting a
  targeted Seat leaves that column inert with its neighbours untouched; and
  removal persisting.
- `tests/verify_event_control_panel.py` run 8× after the change: 8 green (see
  `decisions.md` on the pre-existing detached-node race it started landing on).

## Visual

`shoot.py <dir>` boots the real dashboard + simfleet on the same fixture as the
ratified mockups and shoots the real tab. `control-*.png` beside this file are
1280 / 1680 / 2560 / 760 in dark and light (written flat, not in a
subdirectory — `loom.sh` reads any subdirectory of a stitch as a child stitch
and refuses to tie the parent). Compared against
`.loom/tied/1-columns-design/mockup-*.png`:

| shot | matches the mockup | difference |
|---|---|---|
| 1280 | three columns, left aligned, `+ column` quiet at the left | — |
| 1680 | four columns, the fourth a mixture rendering a card per entry | — |
| 2560 | five columns, the fifth an emptied group with disabled rows | — |
| 760 | scrolls horizontally, columns intact, no reflow | — |

One deliberate departure from the mockups, stated in `decisions.md`: the
strip's right-hand control reads `Capture as Show step` rather than
`capture step · 4/6`, because the ambient count and the armed preview are
`2-venue-wide-capture`'s work.

## Not verified here

Touch. The coarse-pointer pass is `feature-backlog/49-remote-ipad-restyle`, and
Remote is single-column and unchanged by this stitch beyond the picker's
`toggle`-echo fix.
