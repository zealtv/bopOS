# 03-chrome-reclamation — verification

2026-07-30.

## Suites

- `tools/run-tests.sh fast` — **250 tests, OK**.
- `tools/run-tests.sh browser` — **17/17 PASS**, including
  `verify_control_tab.py` with this stitch's five new checks. The
  `47-live-param-kinds-flake` slider assertions did not trip in this run.
- New durable checks (in `tests/verify_control_tab.py`, which already owns tab
  naming and routing): the tab-bar link is named Remote; it points at
  `/facilitator`; it is **outside** `role="tablist"`; the primary tablist still
  holds exactly six tabs (scoped to `#primary-tabs` on purpose — the Seats
  sidebar and Monitor dock are tablists too, which is how the first version of
  this check failed); and the dead Control heading is gone.

## Screenshots

`shoot.py` (copied from `02-token-promotion` and fixed, see below):
every tab at 1280 and 1680 in light and dark, the expanded Monitor dock, the
Remote view and the All card. Retained flattened as `after-*.png`. The matched
"before" for this stitch is `02-token-promotion`'s `after-*.png` set — same
harness, same fixture, one commit earlier.

**The harness was fixed first, and that changes what the dark shots show.** It
wrote `localStorage['bopos.theme']` while `theme.js` reads `bopos-theme`, so
the iframe on the Control tab was never themed and every dark app-control shot
in `02-token-promotion` has a light panel inside a dark app. The theme
`<select>` in these shots reads `Dark` rather than `System`, which is the tell
that the theme actually took. So for the Control tab specifically, compare the
*layout* across the two sets, not the panel's colours.

## Measured reclamation

First content row on the 1280 dark shots, sampled with `PIL` at x=640 below the
tab bar:

| tab | after `02` | after `03` |
|---|---|---|
| Control | 149px | **85px** |
| Assets | 149px | **115px** |
| Patches / Show | 85px | 85px (their headings were inside panels, so the gain is *within* the panel, not above it) |

Chrome above content is unchanged at 73px — that was `02`'s number and this
stitch did not touch the header or tab bar metrics, only what hangs below them.

## Checked by eye in the retained shots

- Control: heading block gone, `Remote` right-aligned in the tab bar.
- Devices: the fleet toolbar is one row — `✕ ↻ ⇧ Shutdown All`. The first
  version stacked vertically because `.device-sidebar footer` (0,1,1) outranked
  the new `.fleet-actions` (0,1,0); the footer rule itself is now the flex row.
- Assets / Patches: refresh is an icon at the top-right of its section head.
- Show: the empty state keeps only its explanatory sentence; the transport strip
  keeps the show name.
- All three glyphs render (the first set, `⌫ ⟳ ↥`, did not).

## Not verified

- Real-browser font rendering of `✕ ↻ ⇧` on Bob's machine — headless Chromium
  draws them, and macOS has broader coverage, but the glyph *choice* for
  "forget offline unbound" and "update bopOS" is a design call flagged for him
  in `decisions.md` rather than a settled one.
- Screen-reader announcement of the tab bar. The structure is right by
  construction (link outside the tablist, six tabs, `aria-label` on every icon
  button) and asserted in the suite, but nothing was driven with a real AT.
