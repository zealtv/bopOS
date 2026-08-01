# §12 ground-and-card audit — 2026-08-01

Every tab, both themes, 1280 and 1680, plus the Monitor dock and Remote. Two
defects found and fixed; every other surface audited and correct. The check is
promoted, but **not** in the form the brief expected — see "The guard" below.

## State of every surface

Ground is `--bg` (`#f8f0fc` light, `#101316` dark). "Correct" means: chrome,
then ground, then cards; ground visible only as gutter; nothing painted on it.

| surface | before | after |
|---|---|---|
| Remote (900px, both themes) | **correct** — the reference implementation | unchanged |
| Control | **correct** — `3-iframe-retirement` had already made the column a card and the tab paint nothing. Pixel-identical before/after | unchanged |
| Show | **defect** — a 1px rule painted on the ground down the full right edge | fixed |
| Seats | **correct** — map card + inspector card, ground as gutter | unchanged (live-data pixel noise only) |
| Devices | **correct** — roster card + detail card | unchanged (live-data pixel noise only) |
| Patches | **correct** | unchanged |
| Assets | **defect** — the refresh button alone on the ground | fixed |
| Monitor dock | **correct** — chrome at the foot, its panels on `--panel` | unchanged |

Two things deliberately **not** changed, recorded so a later reviewer can tell
audited-and-accepted from never-looked-at:

* **`#fleet-patch-panel` is `--surface-alt`, not `--panel`**, so the Patches tab
  shows two top-level cards in different greys. That is a deliberate emphasis on
  the fleet-patch panel, it is a card on the ground either way, and §12 is about
  ground vs card, not about which card colour. Left alone.
* **`.tab-panel` is `background:transparent`** and stays that way. It is the
  ground's window; the fix is always to give the content a card.

## Defect 1 — Show tab: a border painted on the ground

`style.css` carried a bare element rule

    aside{padding:var(--pad-panel);border-right:1px solid var(--line);
          display:flex;flex-direction:column}

left over from the retired two-column `.layout` shell. Three elements are
`<aside>` today. `.seat-sidebar` and `.device-sidebar` restate padding and
border in their own class rule, so they never showed it. The third is
`show.js`'s `.show-inspector-shell` — a **transparent positioning wrapper** —
which had no such rule, so the inherited `border-right` painted a 1px `--line`
rule directly onto the ground, running the shell's full 552px, well past the
bottom of the inspector card. Sampled at (1263, 400): `#ced4da` light,
`#5e6a75` dark — exactly `--line`, on the pink.

This is §12's named mistake in its purest form: a bordered region with no
background.

Fixed by re-anchoring the relic onto the two sidebars that still want it.
`sidebar_cascade.py` measures the result the way `05c` did, serving the app from
a fabricated origin with `page.route` and swapping only `style.css` between
runs: **`.seat-sidebar` 0 of 14 properties changed, `.device-sidebar` 0 of 14**,
and `.show-inspector-shell` exactly 5 — the border, the padding, `display`,
`flex-direction` and the height that follows from them. Nothing else moved.

The shell losing its 10px padding widens the inspector card from 356px to the
full 376px it was allotted, which makes it flush with the tab's right content
edge — **symmetric with the step-list box on the left**, which was already
flush. The old asymmetry was the relic too.

*Fixture gotcha, worth carrying:* the first run of `sidebar_cascade.py` reported
the padding as unchanged. The fixture loaded only `style.css`, but `--pad-panel`
is declared at `:root` in **`control-panel.css`** — the one file both documents
load — so `var(--pad-panel)` was invalid in both measurements and the delta read
`0px -> 0px`. A vacuous pass that looks exactly like a real one. Any fixture
measuring this app's metrics must load `control-panel.css`.

## Defect 2 — Assets tab: a control on the ground

`#asset-refresh` sat in a `.assets-heading` div of its own, directly on the tab
panel. It was not always alone: `03-chrome-reclamation` deleted the tab's `h2`
and description and left the button behind, then pushed it right with a
last-line `.assets-heading{justify-content:flex-end}`. What remained was one
24px button floating on the pink above the first card.

Moved into the head of the card it refreshes, matching `#refresh-distribution`
in the Fleet patch head. `.assets-heading` and all six of its rules are deleted;
`#asset-catalog-panel>.section-head{align-items:flex-start}` keeps the ↻
aligned with the title rather than centred against a three-line block. The tab's
cards also move up 30px, reclaiming the empty div's space.

## Also fixed — a dead §12 declaration

`facilitator.css`'s `.live-param input[type=text]` set `background:var(--bg)` —
a text control painted with the ground colour. It renders nothing today:
`control-panel.css` sets `background:var(--input)` on the same field at higher
specificity (`.live-card .live-param input[type=text]`), and every `.live-param`
on Remote is inside a `.live-card`. So the declaration has been losing the
cascade for its whole life.

Changed to `var(--input)` rather than restructured. The rule is one of the
facilitator duplicates Bob ruled may collapse, but that collapse belongs to
`49-remote-ipad-restyle` and to whichever component reaches the string kind
(`44-event-plane/6-text-kind-control`); this stitch only removes the forbidden
value. Zero rendered change, and the source scan is now clean.

The two surviving `background:var(--bg)` declarations outside the page are both
`.initial-loading` — a `position:fixed; inset:0` boot overlay in each document.
While it is up it *is* the page. Allowed, by name, in the guard.

## The guard — promoted, and not as a source check

The brief proposed `05d`'s shape: a browser-free grep for `background:var(--bg)`
outside `html`/`body`. That scan was written and run (`scan_ground_and_card.py`,
kept here as evidence) and it is **the wrong guard**, which is the most useful
thing this stitch learned. It caught **neither defect**:

* the Assets button had no rule at all — the offending declaration is the one
  nobody wrote;
* the Show rule names neither `--bg` nor the Show tab; it says `aside`.

Both are only visible after the cascade resolves against real markup. Its
companion pattern — an edge with no background — is worse: 51 source hits,
almost all of them pills, dividers and sub-panels correctly showing the card
they sit on, i.e. a guard nobody would keep.

So the promoted check is a browser journey, `tests/verify_ground_and_card.py`.
For every painted element it asks §12's own question — walk up to the first
ancestor that paints a background; if that ancestor is the page, this is on the
ground — across six tabs, the Monitor dock and Remote, in both themes.

Verified by running it against the unfixed tree, where it fails on exactly the
two defects, in both themes, naming the element and its rect. Green on the fixed
tree.

Three things the probe had to get right:

* **a control paints its own face**, so "does it have a background?" cannot be
  the filter for one — every button carries `background:var(--control)`. The
  first draft skipped self-painted elements and reported the Assets button as
  fine. Containers keep that filter (a self-painted container *is* a card);
  controls are always resolved against their ancestors.
* **a closed `<details>` still reports a box** (gotcha 21), so its suppressed
  contents must be excluded structurally or they read as unpainted content.
* **one width is enough, two themes are not.** 1280 and 1680 agreed on every
  surface in both the before and after sweeps — the invariant is about which
  ancestor paints, not where the box landed. Themes stay, because §12 has
  already drifted per-theme once: the 2026-07-30 light repaint missed
  `:root[data-theme="light"]` entirely.

## Verification

* `tools/run-tests.sh fast` — 268 tests, green.
* `tools/run-tests.sh browser` — 24 journeys. The **second** full run was green
  throughout. The first run reported one failure,
  `verify_control_surface_component.py`; that journey then passed 3/3 standalone
  on this tree and 3/3 standalone on a stashed clean tree, and the whole suite
  passed on re-run. Consistent with the intermittent this repo already tracks
  (items 12–14 of the Tier-2 list, where three different journeys failed across
  four runs). **The failing assertion was not captured before the re-run**, so
  this is a plausible attribution rather than a diagnosis — recorded as an open
  loose thread, not as cleared.
* Screenshots: `before-*.png` and `after-*.png`, 30 each (flat, because
  loom reads a subdirectory as a child stitch) (six tabs + Monitor ×
  1280/1680 × light/dark, plus Remote). Pixel-diffed: Control and Remote-dark
  identical; Show and Assets changed exactly where the fixes are; Seats, Devices
  and Patches differ only in live data (RSSI values, roster ordering,
  timestamps), confirmed by crop comparison.
* `probe-before.json` / `probe-after.json` — the raw live findings at both
  widths, both themes.
