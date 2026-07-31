# Verification — 3-iframe-retirement

## Automated

- `tools/run-tests.sh fast` — **255 tests, OK**, including
  `tests/test_css_component_ownership.py` (the guard that decided where the
  card face had to live: `.control-column .live-card{…}` fails it, and
  correctly).
- `tools/run-tests.sh browser` — **20 of 20 journeys PASS**, on the
  post-change tree.

Four journeys were migrated off the frame boundary. Each kept its assertions;
only the reach changed:

| file | was | now |
|---|---|---|
| `verify_control_tab.py:145` | `page.frame_locator("#dashboard-live-view")` | `page.locator("#control-column-host")`, and four `page.frames[-1].evaluate` → `page.evaluate` with `#control-column-host`-scoped selectors |
| `verify_event_control_panel.py:175` | same | same; `live_frame` is `page.main_frame`, and the `#ws-status` wait inside the frame is gone (it was the page's all along) |
| `verify_manifest_param_visibility.py:199` | same | same |
| `verify_preset_control_surface.py:143` | same, plus four raw `contentDocument` evaluates | same; `inner(page)` returns the page, and the evaluates read `#control-column-host` |

`verify_control_surface_component.py` also needed a fix that was not on the
list: its parity probe mounts a fixture with
`document.getElementById("cards").after(…)` on `/facilitator`, and `#cards` no
longer exists. It anchors on `.control-column-cards` now.

One assertion changed meaning rather than reach —
`verify_control_tab.py`'s "the picker follows the Seat chosen on the Seats tab".
D7 retires that behaviour outright, so under CLAUDE.md's supersession rule it is
inverted in place with a comment naming `1-columns-design` D7, and a second
check added that a chip click still aims the column. See `decisions.md`.

## Visual

`shoot.py` (trimmed from the tied `02-token-promotion` harness; writes
`bopos-theme`, not that stitch's recorded `bopos.theme` bug) — Control tab at
1280 and 1680 in both themes, plus Remote in both themes, as `before-*.png` and
`after-*.png` (flat, because the loom counts a subdirectory as an unresolved
child stitch).

What the pairs show, at every width and in both themes:

- **§12 is delivered.** `before-*` is the iframe's bordered box painted in
  `--bg`, with the panel sitting inside it — Bob's "swimming in empty space".
  `after-*` is one card on the ground with no inner box at all.
- **The panel is no longer clipped.** The iframe was `58vh`/`min-height:520px`,
  which cut the manifest off mid-list (the `reverb` and `delay` branches were
  below the fold at 1280). The column grows to its content.
- **Light theme is the ratified neutral card on the pink ground**, not a
  pink panel.

The `after-*` set was reshot once, after the `Capture as Show step` casing fix — the
first pass caught the dashboard document's `button{text-transform:capitalize}`
reaching a control that had never met it.

## Measured

`remote_delta.py --diff remote-before.json remote-after.json` →
`remote-delta.txt`. 55 controls on the live Remote page; 30 width-only, 4
substantive. Summarised in `decisions.md` and recorded in
`feature-backlog/49-remote-ipad-restyle`.

## Not verified here

- **Touch.** Playwright's coarse-pointer emulation is not a finger; the Remote
  view's tap targets are `49`'s, and hardware-gated.
- **Real PD / a live fleet.** simfleet speaks the protocol, not audio.
