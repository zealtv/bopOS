# 03-chrome-reclamation — decisions

2026-07-30. Bob: *"there's a lot of wasted real estate … that text isn't doing
anything. We don't need it at all."*

## Headings: deleted three, kept two, on one test

The test the instructions set is *does it carry information the tab bar
doesn't?*

| site | verdict |
|---|---|
| `index.html` Control — "Live control" / "Control" | **deleted**, whole block |
| `index.html` Assets — "Single-device delivery" / "Assets" | **deleted** |
| `index.html` Fleet patch — "Live fleet deployment" / "Fleet patch" | eyebrow deleted, **`<h2>` kept** — the Patches tab has two sections and this names one of them |
| `show.js:455` empty state — "Show control" / "Show" | **deleted**; the `<p>` under it ("Create or load a show…") is the only informative line, so it stays |
| `show.js:487` transport strip — "Show control" / show name | eyebrow deleted, **`<h2>` kept** — it is the *show name*, which nothing else on screen says |

Every `.eyebrow` in the app is now gone, so its rule went with it. Two more
rules died with the markup and were deleted rather than left: the
`.dashboard-heading` pair, and `.placeholder-tab`, which outlived the Monitor
Map placeholder Bob dropped on 2026-07-26.

Measured on the 1280 dark shots: first content on the **Control** tab moved
149px → **85px**, and on **Assets** 149px → **115px** (the icon button's row
plus one `--gap`).

## The Remote link

`<a href="/facilitator" id="facilitator-link">Remote</a>` now sits in the tab
bar, right-aligned via `margin-left:auto`, **outside `role="tablist"`**. To do
that the nav had to stop being the bar: `.primary-tabs` is now a wrapper div
(it keeps the class, so the sticky positioning and every `.primary-tabs button`
rule still apply) and the nav inside it is `.primary-tab-list`, still
`id="primary-tabs"` with `role="tablist"`. Tab wiring is `[data-tab]`-based
(`dashboard.js:74`), so no JS changed. Five durable checks went into
`tests/verify_control_tab.py`, which already owns tab naming and routing —
including that the link is outside the tablist and that the primary list still
holds exactly six tabs.

## Icon buttons: five converted, two declined

Converted, each with `title` + `aria-label` and a square `--row-h` box:
`#asset-refresh` and `#refresh-distribution` (↻), and the three recoverable
fleet actions — forget offline unbound (✕), reboot all (↻), update bopOS (⇧).
**`Shutdown All` keeps its words** per the instruction. All four fleet actions
still route through their existing `confirm()`, which names the verb, so a
mis-clicked glyph cannot act on its own.

Glyph choice is deliberately conservative: `⌫`/`⟳`/`↥` were tried first and
render as tofu in headless Chromium, so the set is the one this app already
proves it can draw (the edit bar's `✕`/`⧉`/`✛`/`╱`) plus basic BMP arrows.
**The weakest part of this stitch:** `✕` for "forget offline unbound" and `⇧`
for "update bopOS" are guessy without their tooltips. They are cheap to change
and worth Bob's eye.

Declined, with reasons rather than silently:

- **`#editor-session-actions` / `.mode-actions`** is not a repeated toolbar. It
  holds one conditional button — `Relaunch`, rendered only when the editor
  engine has closed (`dashboard.js:1003`). A rare recovery action is exactly
  where a word beats a glyph.
- **`.fleet-patch-actions`** is `Deploy as fleet patch` + `Revert`: two
  consequential, non-repeated actions whose labels are the affordance. That row
  is also the whole subject of **`09-patches-deploy-row`** ("patch, target,
  actions on one line"), so shortening it here would pre-empt a stitch that
  owns it.

## One disclosure treatment

All eight `<details>` now share one marker, promoted from
`control-panel.css` §14 where design-language §9's ratified `▸`/`▾` shipped
panel-only: base `details>summary` rules in `style.css` **and** `facilitator.css`
(that page does not load `style.css` — same reason the token block lives in
`control-panel.css`). The two glyph-summary menus, `.group-overflow` and
`.monitor-tab-menu`, opt out with a new `.icon-menu` class: their summary *is*
an icon button, and a marker beside the glyph reads as two controls. The
control panel's own more-specific rule still wins inside the panel, so nothing
there changed.

## Two bugs found in passing, both fixed

1. **The screenshot harness was lying about dark mode.** `shoot.py` wrote
   `localStorage['bopos.theme']`, but `theme.js` reads **`bopos-theme`**
   (`theme.js:4`). Nothing consumed the key it set; the parent document only
   looked themed because the same `evaluate` also assigned
   `documentElement.dataset.theme` by hand — which the Control tab's **iframe**
   never saw. So every dark app-control shot in `02-token-promotion`, before
   *and* after, shows a light panel inside a dark app. Fixed with the right key
   in an `add_init_script` (it runs in every frame, before page scripts), and
   the theme `<select>` in the new shots now reads `Dark` instead of `System` —
   which is how you can tell the evidence is honest.
2. **`theme.js` still painted the old lavender ground.** Its
   `meta[name=theme-color]` for light was `#f4f1f8`, superseded by `#f8f0fc`
   in the 2026-07-30 repaint. One value, now consistent with the CSS.
