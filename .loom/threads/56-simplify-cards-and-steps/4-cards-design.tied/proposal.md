# Cards grid proposal

Status: ratified by Bob on 2026-08-02. This revision incorporates his review
of the first mockups.

## The model

One `CardsGrid` renders cards in this derived sequence:

1. All Seats;
2. groups, ascending by numeric id;
3. Seats, ascending by numeric id.

Each card has exactly one selector and therefore one server target: `all`, one
`gN`, or one Seat id. There is no multi-selection inside a card, no authored
card order, and no drag affordance. This keeps preset and parameter traffic on
the server's coalesced single-selector path.

Control and Remote deliberately differ in membership, not in card anatomy:

- **Control** renders the operator's persisted set of cards. `+ card` creates a
  target draft; choosing a target commits it to the set. Every card retains a
  single-select target picker and a close action.
- **Remote** derives the exhaustive set — All, every group, every Seat — and
  shows labels instead of pickers. Cards cannot be added, closed, or
  retargeted there.

Both sets are sorted by the same All → groups → Seats function after every
venue or selection change. Control add order is never presentation order.
Duplicate targets are not allowed: targets already represented by another
Control card are disabled in a draft or retarget picker. Retargeting changes
the existing set member atomically, then the card moves to its derived place.

## Control persistence and strip

`bopos.control.columns` is replaced by a versioned set of target selectors;
minted column ids, per-column picker-open state, and stored order retire. The
implementation may migrate the valid, unique targets from the old records
once, but the new authority contains only membership. Invalid targets are
pruned after `venueKnown`, using the existing race-safe venue gate.

The Control strip remains, reduced to `+ card`. It creates at most one
transient empty draft, opens that draft's picker, and focuses its first
available target. The draft is not persisted until a choice is made. Cancelling
or closing it leaves no state. Closing the last committed card is allowed; the
empty grid keeps the strip and an ordinary “Add a card to begin” empty state.

The Seats → Control action switches tabs and focuses an existing card for that
Seat. If none exists, it adds that target to the set first. This is the one
cross-tab path that may create a card without showing a draft.

## Grid and scrolling

342px remains the minimum proven width for a parameter row, generator drawer,
and 58px value box. It is now a minimum rather than a fixed track:

```css
grid-template-columns: repeat(auto-fit, minmax(min(342px, 100%), 1fr));
align-items: start;
gap: 12px;
```

The tracks divide the remaining horizontal space evenly. Thus a 1280px host
still yields three cards, but the unused part of the would-be final track is
shared across those three instead of collecting as dead space at the right.
At less than 342px the single track shrinks with the viewport; horizontal
overflow is never introduced.

Cards are full-content-height and the page is the only vertical scrollport.
The existing `grid-template-rows:auto minmax(0,1fr)` column clamp,
viewport-height host calculation, per-column `overflow-y:auto`, and
`verify_control_column_scroll.py` retire. Later cards are reached by scrolling
down, never sideways or inside a nested panel.

## Card head and identity stroke

On Control the card head is the closed single-select target picker plus close.
Its disclosure contains All, group, and Seat choices in the established picker
order. Metadata remains immediately below/alongside it:

- `All Seats · N Seats`;
- `<group name> · gN · N Seats`;
- `<seat name> · Seat N · online/offline/unbound`.

On Remote the same head position is a non-interactive label and metadata. Grip
and multi-select summary chrome leave both hosts.

The card border identifies its target:

- All uses a thick white stroke. It is backed by the map's dark keyline
  (`#071015`) so the white remains legible on the light theme.
- A group uses its active Seats-tab map slot colour and stroke pattern:
  `#56B4E9` solid, `#E69F00` dashed, `#00B98B` dotted, or `#CC79A7`
  dash-dot. CSS borders cannot express the rail's dash-dot sequence exactly;
  slot 4 uses the existing Seats-tab `double` border equivalent.
- A Seat keeps the neutral card border.

Map slots are presentation assignments, not group data. A group card therefore
updates as visibility/slot assignment changes; a group without a current map
slot uses the neutral border until assigned. None of the four generated group
colours is white.

This border is **target identity**, not preset provenance. The shipped
`PresetMenu` remains the only treatment for deviated, missing, foreign-patch,
and schema-drift state. Cyan remains reserved for modulation/fire feedback.

## Control and Remote convergence

Both documents mount the same `CardsGrid` and `liveCard` / `ControlSurface`
component. Remote cards are naturally shorter because `dashboard:true`
continues to filter declarations there; Control continues to show the full
manifest. Remote's venue header, master, SILENCE ALL, and per-device lifecycle
commands remain because the desktop document has dedicated Monitor and Devices
surfaces.

Remote has **no presets for now**: neither recall nor authoring is rendered.
The existing `full` boolean should split into named capabilities such as
`fullManifest`, `presetMenu`, `targetPicker`, and `deviceCommands`. This is one
surface with explicit host capabilities, not two rendering models hidden
behind one flag. `feature-backlog/49-remote-ipad-restyle` still owns touch
sizing and page-furniture polish, not a divergent card model.

## What implementation changes

- replace Control's ordered column records with a unique persisted target set;
- keep add, close, and single-select retargeting on Control, but delete drag,
  grip, stored order, multi-selection, and per-card scroll state;
- make the Control strip an add-only strip;
- derive every Remote target and remove its picker and presets;
- share one sorting function and responsive downward grid across both hosts;
- apply All/group identity borders without duplicating provenance state;
- replace column-scroll and drag/order journeys with target-set persistence,
  duplicate prevention, flexible track, exhaustive Remote, identity-stroke,
  page-scroll, and focus-card journeys.

No server, OSC, manifest, preset data, Show, or Pure Data change is implied.

## Mockups

`mockup.py` asks the shipping `ControlSurface` and `TargetPicker` JavaScript to
render current controls, then composes those real components into the ratified
shell. Control intentionally shows a subset plus its add strip; Remote shows
every target without a picker or preset menu. Both themes show flexible tracks
and All/group identity strokes.

This managed run cannot launch macOS Chromium because the sandbox hides the
system appearance bundle. The checked-in PNGs therefore use the script's
fallback: shipping component markup and styles rasterized by WeasyPrint. The
matching HTML is reviewable source. Running the script in a normal repo shell
takes the preferred live-dashboard path.
