# Cards grid proposal

Status: proposed for Bob's review. R1–R4 are settled inputs; Q1–Q3 below are
the remaining choices this design does not silently ratify.

## The model

One `CardsGrid` renders one card for every target in this derived sequence:

1. All Seats;
2. every group, ascending by numeric id;
3. every Seat, ascending by numeric id.

Each card has exactly one selector and therefore one server target: `all`, one
`gN`, or one Seat id. There is no selection array in the UI model. This keeps
preset and parameter traffic on the server's coalesced single-selector path
and makes the visible order a projection of venue state rather than authored
layout state.

This is intentionally the strongest simplicity reading of R1–R3: every target
always has a card. A new group or Seat appears in derived order; deletion
removes it. An empty group remains as a disabled, named card. An unbound or
offline Seat remains visible with its existing state. A venue with no Seats
still renders the All card's honest empty state.

### Q1 — should every target always have a card?

Recommendation: **yes**. This deletes `bopos.control.columns`, minted column
ids, stored target/open state, migration from `bopos.target.control`, `+`, close,
drag, pruning, and the entire lost-target restoration path. It also makes R3's
derived order literal.

The cost is vertical length at large venues. The alternative is to persist the
set of open targets, sort that set by R3, and retain `+`/close. That saves page
length but preserves almost all of the state and chrome this redesign can
remove. The proposed grid makes the cost visible and ordinary: page scroll.

## Grid and cards

Cards retain the proven 342px width. The parameter row, generator drawer, and
58px value box were designed and measured inside that track; widening cards
does not improve their information density, while narrowing them would reflow
the control component.

Desktop grid:

```css
grid-template-columns: repeat(auto-fill, 342px);
align-items: start;
gap: 12px;
```

Below one 342px track plus page gutters, the grid becomes one fluid track
(`minmax(0, 1fr)`). It never creates horizontal overflow. Width buys another
card; it does not stretch existing cards. The 1400px cap remains absent on
Control, so 1280px shows three cards and 1680px shows four.

Cards are full-content-height and the page is the only vertical scrollport.
The existing `grid-template-rows:auto minmax(0,1fr)` column clamp,
viewport-height host calculation, per-column `overflow-y:auto`, and
`verify_control_column_scroll.py` retire. R2 is therefore observable: later
cards are reached by scrolling down, never sideways or inside a nested panel.

### Q2 — ratify 342px fixed tracks?

Recommendation: **yes**. It preserves the shared ControlSurface geometry and
makes the change about hierarchy and navigation, not a simultaneous parameter
row redesign. If cards should stretch to consume the last partial track, that
is a different visual ruling and the mockups deliberately do not assume it.

## Card head

The target picker becomes a label. With one permanent card per target, a
picker can only retarget a card into a duplicate or create a missing target;
both contradict the derived projection. The existing live-card head already
contains the correct label and metadata:

- `All Seats · N Seats`;
- `<group name> · gN · N Seats`;
- `<seat name> · Seat N · online/offline/unbound`.

Seat health and the existing overflow hand-offs remain. Grip, close, target
disclosure, terse duplicate title, and column region wrapper leave. Each card
itself becomes the labelled region, so keyboard and screen-reader order is the
same all → groups → Seats order as the visual grid.

## Persistence and strip

`bopos.control.columns` is deleted, not migrated. There is no new persistence
key because the grid is fully derived. The legacy target key and its open-state
companion stop being read by Control. `venueKnown` remains only as an initial
render gate so the page does not flash an empty venue before state arrives; it
no longer protects persisted picker state. D5 pruning and gotcha 20's
device-update race disappear with the state they guarded.

The Control strip is deleted. Capture already left in `1-capture-retirement`;
with `+ column` gone it has no content, layout role, or reason to paint a bar.

The explicit Seats → Control action changes from “focus or append a column” to
“switch to Control and scroll/focus the already-derived Seat card.” It creates
nothing and persists nothing.

## Control and Remote convergence

Both documents mount the same `CardsGrid` and the same `liveCard` /
`ControlSurface` component. Remote gets the same all → groups → Seats grid and
the same page-scroll model. Its cards are shorter because `dashboard:true`
continues to filter declarations there; Control continues to show the full
manifest. Remote's real page furniture (venue header, master, SILENCE ALL) and
its per-device lifecycle commands remain because the desktop document has
dedicated Monitor and Devices surfaces.

The existing `full` boolean should split into named capabilities rather than
continue bundling unrelated differences: `fullManifest`, `presetAuthoring`,
and `deviceHandoff`/`deviceCommands`. This is one surface with explicit host
capabilities, not two rendering models hidden behind one flag.

### Q3 — should Remote gain preset recall/authoring?

Recommendation: **no in this stitch**. R4 settles the card/grid surface and
explicitly explains Remote's shorter manifest subset; it does not explicitly
reverse preset primitive Q4, which removed presets from Remote rather than
rendering them inert. Preserve that ruled capability difference while making
the structure identical. If “same surface” was intended to reverse Q4 too,
say so here and implementation can enable the already-shared `PresetMenu`.
The touch treatment remains owned by `feature-backlog/49` either way.

## Provenance

No second treatment is designed. `53-ui-niggles/3-preset-dropdown-menu` now
owns the closed preset readout and distinctly presents deviated, missing,
foreign-patch, and schema-drift state at the leading edge. That row travels
unchanged inside each Control card. Remote continues without it unless Q3 is
reversed.

In particular, the card gets no provenance border, tint, header chip, or
duplicated status words. This follows both relevant consults, preserves §12's
one-card face, and avoids making one state compete with focus, disabled/empty,
and device-health channels.

## What implementation deletes

- ControlHost's layout read/write, id minting, mount/remove, drag/reorder, sole
  column state, and add button binding;
- ControlColumn's target picker, target/open persistence hooks, selection
  algebra, unresolved-target path, column shell, and per-column scroll state;
- the Control strip and `bopos.control.columns` persistence contract;
- target-picker usage on this surface only (other consumers keep multi-select);
- column-scroll and N-column persistence/drag journeys, replaced by grid order,
  all-target coverage, one page scrollport, Remote convergence, and focus-card
  journeys.

No server, OSC, manifest, preset, Show, or Pure Data change is implied.

## Mockups

`mockup.py` boots the real dashboard and simfleet, asks the shipping
ControlColumn/ControlSurface code to render one target at a time, and only
recomposes those real cards into the proposed grid shell. It produces both
themes for desktop Control and the real Remote document. The mockup CSS is the
proposed shell; every event, parameter, preset row, status, and card head is
shipping markup and shipping component styling.

This managed run could not launch macOS Chromium because the sandbox hides the
system appearance bundle. The checked-in PNGs therefore use the script's
fallback: current ControlSurface markup rendered by the shipping JavaScript,
current component stylesheets, and the same proposed shell, rasterized by
WeasyPrint. The checked-in HTML is the reviewable source. Running the same
script in a normal repo shell takes the preferred live dashboard path.
