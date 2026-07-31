# 08-control-tab-columns

**Goal:** the Control tab hosts N control-panel columns instead of one iframed
panel, each with its own target.

**Split into four children on 2026-07-30.** As one stitch it bundled a
Bob-gated design gate, a cross-document structural refactor, a state-model
change from singleton to N, and a four-file test migration.

| | scope | gate |
|---|---|---|
| `0-prune-fallback-safety` | a live target-widening defect the consult found; D5, pulled out so it does not wait on the thread | none |
| `1-columns-design` | proposal + mockups; the open questions; the capture-as-step UX consult | **TIED 2026-07-31** |
| `2-control-column-component` | extract `ControlColumn` from `facilitator.js` — instance state, no module globals. Still inside the iframe, zero visual change | none |
| `3-iframe-retirement` | mount in the parent document, `/facilitator` becomes Remote-only, §12 ground fix, migrate the four journeys, delete gotcha 15. N stays 1 | none |
| `4-n-columns` | add/remove, per-column target, persisted layout, columns as cards | unblocked |

## `1` is ratified — the design of record (Bob, 2026-07-31)

`.loom/tied/1-columns-design/` holds `decisions.md` (authority), `proposal.md`,
`judgment.md`, three `expert-*.md` consults, `ground-truth.md`, and mockups
generated from the real running app by `mockup.py`.

**The consult question had a wrong premise.** All three UX lenses independently
answered *neither* per-column nor whole-tab: **capture is venue-wide and takes
no scope argument**. Per-column capture is not "easiest" — it is wrong today,
because a group column sends `scope:"groups"` and the server then captures every
grouped seat in the venue. And the instructions' warning about a "widened server
vocabulary" was backwards: widening is the cost of the *per-column* answer;
venue-wide capture is a removal.

Nine decisions, all ratified, D7 amended by Bob to "never" (no ambient
focus-seat follow at any N). D5 became `0-`; D8 is a behaviour change Bob ruled
in (device commands leave the Control column, preset authoring demotes,
`Send all` to an overflow). Details in `4-n-columns`.

Two findings went to siblings rather than being settled in the design: the
document-wide fade animator (`2`) and the card chrome that lives in
`facilitator.css`, which `index.html` does not load (`3`).

`0`, `2` and `3` are unblocked and can run in any order. Splitting `2` from `3` is
the load-bearing decision: it puts the singleton-to-instance extraction behind
an unchanged iframe boundary, where the existing four journeys still guard it,
so a break is attributable to the extraction and not to the document move.

Ordering dependency for the whole thing: `07-target-selector-component`, which
is tied.

Today the Control tab is one iframe (`index.html:31`,
`#dashboard-live-view` → `/facilitator?embedded=1`), with the target picker
inside it.

## Bob's rulings, 2026-07-30 (carried into the children)

- The control panel *"works really well when it's a relatively narrow column"*
  → N columns, each with its own pop-out target selector, targeting all / a
  selection of groups / a selection of seats / a mixture. Simple add and
  remove, **minimum one**, so the tab is never empty. The All/Groups/Seat radio
  row goes away.
- **RETIRE THE CONTROL-TAB IFRAME.** `ControlSurface` is hosted directly in the
  parent document; `/facilitator` becomes the standalone **Remote** view only.
  This removes the cross-document coordination that `control-panel.css`'s
  header and CLAUDE.md Playwright gotcha 15 both exist because of; gotcha 15
  gets *deleted* from CLAUDE.md once it stops being true. → `3`
- **Column layout persists in `localStorage`** — consistent with
  `bopos.control.collapsed-branches` and `bopos.device-control-open`. Bob:
  *"with a chip picker it should be easy to spin up whatever control panel
  targets one needs"* — cheap re-creation is the argument against needing
  durable server-side layout. → `4`
- **Capture-as-step ownership** gets a UX consult before a default is taken.
  Bob: *"per column seems perhaps easiest — but if an all-column
  capture-as-step workflow makes sense it's worth considering."* → `1`

## Settled in `1` — do not re-decide

Column widths (fixed 342px, left-aligned, cap dropped); the no-seats state
(inert, never widened); the applied-preset marker across overlapping columns
(nothing needed — provenance is per seat and derived, so two columns render one
fact twice); `followFocusSeat` (retired on Control, replaced by an explicit
"Open in Control"); capture-as-step ownership (venue-wide, no scope).

## Ground and card (Bob's tab-by-tab review, 2026-07-30)

Retiring `#dashboard-live-view` also retires the app's clearest design-language
**§12** violation: that iframe sets `background:var(--bg)` and a border, so the
Control tab shows a bordered pink box with the panel swimming in it (Bob's
words: *"swimming in empty space"*).

§12: `--bg` is the workspace ground, visible only as gutter *between* cards, and
nothing but the page may set it. So when `4` lays out N columns, the columns are
cards on the ground — the ground shows as the gap between them, and never inside
a column's footprint. `3` deletes the `background:var(--bg)` declaration with
the iframe rather than porting it to the column container.
