# Seat-group spatial membership UX proposal

Status: **ratified by Bob on 2026-07-16**. Bob ratified the four original
questions (focus/four-group rail comparison, view-local styles, checklist
authoring, and empty live-target behaviour), made eye/eye-off visibility
iconography binding, and accepted the hierarchy review's subordinate,
collapsible Groups placement after Seat detail and before Simulation/Venue.

## Recommendation

Add a compact, collapsible **Groups** inspector *after the Seat roster and
selected-Seat detail* in the Seats sidebar. It is a secondary management/layer
section, never the top-level heading. Show group membership on the existing
spatial map as separate, concentric outline rails around each Seat element.

The interaction has two deliberate levels:

1. **Focus** answers “where is this group?” Selecting a group focuses it,
   ensures it is visible, strengthens its rail, and de-emphasises non-members.
2. **Compare** answers “how do these groups overlap?” An independent eye
   control keeps up to four groups visible at once. Each visible group owns one
   rail slot, so an overlapping Seat shows several discrete rings rather than a
   mixed colour.

The group name and immutable token (`g3`) remain the identity everywhere.
Colour is only a view-local aid. No colour field is added to the ratified group
data model.

The accompanying `prototype.html` is a standalone visual study of the proposed
focus, compare, hover/tap and clear behaviours. It uses representative data and
does not import or change production code.

## Why rails

The current map already assigns Seat element **fill colour** by element index,
uses white outline for selected Seat, amber outline for crashed state, and draws
coloured Point fields behind the Seats. Recolouring the dot would erase element
meaning; tinting the whole Seat would merge memberships; and large filled halos
would collide with Point fields.

Membership rails sit behind the element dot and outside its operational status
outline:

```text
    rail 4   ─ ─ ─ ─       one rail per visible group
    rail 3   · · · ·
    rail 2   ━━━━━━━
    rail 1   ───────
    Seat     ● 12           fill still means element index
```

Every element of a multi-element Seat receives the same membership rails,
because membership belongs to the Seat, not an element or physical device. The
existing line joining a pair remains visible. Rail slot, dash pattern, colour,
and the numbered legend marker are redundant encodings; no decision requires
colour recognition.

## Proposed Seats workspace and hierarchy

Keep the existing map/sidebar split and preserve its information hierarchy:
the spatial Seat map is primary; the sidebar starts with the **Seats** heading,
Create Seat, Seat roster, then selected-Seat detail. Add Groups as a lower,
collapsible `h3` section after Seat detail and before the existing Simulation
status and Venue utilities:

```text
Seats                                  Create Seat
Seat roster
Selected Seat detail

▾ Groups                         Create group
   Search groups…
   1  Front row       g1    8 Seats    [eye]  …
   2  Guitars         g2    5 Seats    [eye]  …
   –  Roving          g7    3 Seats    [eye-off] …
   Clear group view

Simulation status
Venue
```

The Groups disclosure header shows a quiet summary such as “2 shown · 6 total”
when collapsed. This keeps the normal Seat-selection task compact while leaving
comparison state visible. Opening it does not change the map; collapsing it
does not hide groups. The map legend remains above the map whenever any group
is visible, so active overlays never become invisible state.

Each group row has four distinct actions:

- Tap/click the row to focus it; tap the focused row again to remove focus but
  leave its eye state unchanged.
- Toggle the trailing eye/eye-off button to show/hide it in comparison without
  editing membership. An open eye means currently shown; a slashed eye means
  currently hidden.
- Use the overflow menu to rename or delete it.
- The numbered, styled marker mirrors the map rail and legend. Screen-reader
  text says “comparison style 2”; colour is never the accessible name.

The map header shows the visible groups as wrapping legend chips, in rail order,
and a **Clear group view** button. Clear removes focus and all visible group
overlays; it never changes group membership. `Escape` removes focus first, then
clears comparison on a second press when focus is already absent. The explicit
button remains the discoverable and touch-safe route.

### Placement alternatives

#### A. Subordinate collapsible sidebar section after Seat detail — recommended

This matches the current object hierarchy: Seats are authored and selected
first; Groups organise those Seats. It keeps group catalog, membership actions,
and selected-Seat context in one sidebar without interrupting the roster/detail
relationship. It is discoverable but visually secondary (`h3`, disclosure,
quiet Create group). Its cost is vertical depth when a detailed Seat editor is
open; the collapsed summary and sticky-on-open section header should mitigate
that without promoting Groups above Seats.

#### B. Map-layer popover/drawer

A Layers button near the map legend is a strong home for visibility toggles and
comparison focus. It is a weak home for create/rename/delete and member
checklists: those object-management tasks become hidden in a transient overlay,
the drawer competes with the map on iPad, and the same catalog would likely be
duplicated in Seat detail. Reject as the sole placement. A compact Layers button
may become a later shortcut that opens/focuses the canonical sidebar section.

#### C. Permanent section between Seat roster and Seat detail

Highly discoverable, but it separates the selected Seat from its details and
makes a secondary grouping concept dominate the primary select→inspect flow.
Reject.

#### D. Permanent top-of-sidebar Groups section

Rejected. It makes Groups appear peer or superior to Seats even though groups
contain Seats, and pushes the primary Seat roster below a potentially long
catalog. This was the first prototype's hierarchy error.

#### E. Venue utility beside Simulation/Venue

Correctly quiet, but too low and semantically misleading: groups are authored
installation objects and map layers, not a save/load utility. The recommended
position is immediately before these utilities, not inside them.

## Visibility icon convention and source review

The repository currently has no web icon library, icon font, package manager,
or reusable inline-SVG system. Production dashboard controls are plain
HTML/CSS/JS; the only icon-named asset is the raster application icon. Adding a
runtime icon dependency or externally hosted font for two glyphs is
disproportionate.

Use a matched, vendored inline SVG pair: **Lucide `eye` and `eye-off`**, 20–22 px
inside the existing 44 px touch button. Lucide provides both as plain SVG and
documents their visibility semantics on the official [`eye`](https://lucide.dev/icons/eye)
and [`eye-off`](https://lucide.dev/icons/eye-off) pages. The set is ISC-licensed;
if these SVG paths land in production, retain Lucide's copyright and permission
notice in the repository's third-party notices as required by the
[`LICENSE`](https://github.com/lucide-icons/lucide/blob/main/LICENSE). The
prototype embeds only these two paths and adds source attribution in an HTML
comment; it does not add a Lucide runtime.

Two suitable alternatives were reviewed:

- Google's current [Material Symbols guide](https://developers.google.com/fonts/docs/material_symbols)
  offers `visibility`/`visibility_off` under Apache 2.0, including downloadable
  SVG, but its easiest web integration is a font and therefore adds loading and
  self-hosting concerns this dashboard does not otherwise have. Vendored SVG
  would require retaining the Apache 2.0 license/notice obligations described
  in the official [icon repository](https://github.com/google/material-design-icons).
- Microsoft's [Fluent System Icons](https://github.com/microsoft/fluentui-system-icons)
  offers `Eye`/`Eye Off` as plain SVG under MIT. It is equally viable, but Lucide's
  simple stroke language fits the dashboard's existing outline controls and is
  easier to recolour with `currentColor` without importing a framework. Fluent
  would require preserving its MIT copyright/license notice.

The convention itself is well established in both contexts Bob named:

- Figma's official [Layers visibility help](https://help.figma.com/hc/en-us/articles/360041112614-Toggle-visibility-to-hide-layers)
  says the eye closes when a layer is hidden and the layer row becomes inactive.
  Group overlays are directly analogous map layers, so the glyph should depict
  **current state**: open eye = shown, eye-off = hidden.
- Microsoft Edge's native [password reveal control](https://learn.microsoft.com/en-us/microsoft-edge/web-platform/password-reveal)
  uses an eye-shaped reveal control and changes it to a slashed eye when content
  becomes visible. That confirms familiarity but also exposes a semantic trap:
  password controls may depict the *available action* while design-layer panels
  depict *current visibility*. Because this is a layer list, bopOS follows the
  Figma/state convention and does not borrow password action semantics.

The button is a native `<button aria-pressed="true|false">`. Its accessible name
and tooltip state the **next action** (“Hide Front row from map” / “Show Front
row on map”), while the icon depicts current state. This follows Material's
[accessibility guidance](https://m1.material.io/usability/accessibility.html)
to use a native boolean control for an item property and provide meaningful
action text rather than naming the icon. Icon-only controls retain the 44 px
touch target and a visible keyboard focus ring.

The fifth eye is not silently substituted: it remains unchecked and an inline
message says “Four groups are already shown; hide one to compare another.” This
keeps rail identity stable and prevents an accidental loss of context.

### Focus state: one selected group

- The focused group receives the thickest/highest-contrast rail.
- Member Seats remain at full opacity; non-members are muted to about 30%, but
  never removed. Room topology and authoring targets therefore remain legible.
- The sidebar row, map legend chip and rail all share the same selected state.
- An empty focused group produces no rails and shows “No Seats in this group”
  above the map; this is not confused with a rendering failure.

### Compare state: several visible groups

- Up to four rails render from nearest to farthest around every member Seat.
- A Seat in several groups shows several separate rails with dark spacing
  between them. No alpha blending, wedges, gradients or mixed colour is used.
- With no focus, Seats in any visible group remain at full opacity and Seats in
  none are muted to about 55%.
- Focusing one of the compared groups strengthens its rail and mutes the other
  rails without hiding them. This supports “find Front row inside the overlap”
  without destroying the comparison.

### Hover, tap and selection

- Pointer hover may show `Seat 12 · Front row, Guitars`, but it is supplementary.
- Tap/click still selects a Seat and opens existing Seat detail; it does not
  toggle membership. This avoids overloading the current drag/select gesture.
- Selected Seat remains visibly selected with the existing white operational
  outline above the membership rails. Its detail panel lists all memberships,
  including currently hidden groups, using names plus canonical tokens.
- Keyboard focus on a Seat exposes the same accessible description as hover.

## Group authoring

Group creation, rename and deletion live in the Groups inspector. Membership
can be edited from either object without introducing a map gesture mode:

- In **Seat detail**, a searchable “Groups” checklist adds/removes that Seat
  from several groups.
- In **Group detail**, a searchable “Members” checklist adds/removes several
  Seats from that group.

Both are views of the same Seat membership state and update together. There is
no drag-box, paintbrush or “tap Seats to add” mode in version 1: those modes
collide with map positioning and are easy to trigger accidentally on iPad.
Every checked row shows both display name and durable identity (`Seat 12` or
`g3`), and save/synchronisation feedback belongs beside the edited checklist.

Selecting a membership checkbox does not unexpectedly change map focus. A
small **Show on map** action in group detail focuses that group when desired.
When the focused group's membership changes, rails update immediately from
canonical dashboard state; acknowledgement/convergence status remains a data
and delivery concern of the core stitch, not a new map meaning.

## Live-control target consistency

The later Dashboard live-control target picker should use the same conceptual
row, not necessarily the compact map legend:

```text
All Seats
Front row     g1     8 Seats
Guitars       g2     5 Seats
Seat 12
```

Rules shared by authoring and live control:

- group display name first, canonical `g<id>` always visible nearby;
- the current member count shown before targeting;
- empty groups disabled as live targets with “No Seats”, but still editable and
  inspectable in Seats;
- deleted groups disappear from both places in the same state update;
- rename changes the label but never the token or current target identity;
- selecting a live-control Group target offers **Show in Seats** (or preserves a
  shared selected-group ID) so the same group can be focused on the map;
- colour/rail slot is not copied into OSC, presets, venue state, or target
  identity. Live controls never say only “the blue group”.

This keeps group choice consistent while respecting the program boundary:
stitch 12 owns live controls and this design does not implement them.

## Colour and non-colour encoding

### Recommended policy

Styles are **view-local comparison slots**, assigned in the order groups become
visible and retained until each is hidden or the view is cleared. A slot combines:

- rail distance (1 nearest through 4 farthest);
- a high-contrast dark under-stroke and coloured top-stroke;
- distinct line treatment (solid, long dash, dots, dash-dot);
- a visible numeral 1–4 in the legend.

Candidate palette on the existing dark room: sky blue `#56B4E9`, orange
`#E69F00`, bluish green `#00B98B`, and pink-purple `#CC79A7`. Final production
colours need contrast measurement against `#12171c` at rendered stroke widths.
The palette is adapted from common colour-vision-safe pairings, but position,
pattern, numeral and text do the semantic work.

View-local styling is preferable to authored colour because:

- the ratified model needs no decorative field or migration;
- every currently compared group is guaranteed a distinct style;
- authors cannot choose low-contrast or indistinguishable combinations;
- a large catalog is not forced into a finite global palette.

The cost is that a group may use a different slot in another comparison. That
is acceptable because the UI always presents name plus token, and because
colour is a temporary comparison instrument rather than group identity.

### Accessibility and adverse rooms

- Never communicate membership by colour alone.
- Keep Seat ID text and operational state above rails.
- Use dark separation between adjacent rails and a pale focus edge so projection
  washout does not turn adjacent colours into one band.
- Maintain at least 3:1 contrast for meaningful graphical strokes and 4.5:1 for
  normal legend text; verify rendered values rather than assuming palette names.
- Respect forced-colours/high-contrast mode by rendering numbered rail markers
  and distinct solid/dashed outlines using system colours.
- `prefers-reduced-motion` disables rail transitions; the proposal needs no
  pulsing or animated glow.
- Every eye, row, menu and clear control has a 44 × 44 CSS-pixel touch target.
- Hover is optional; tap and keyboard routes expose the same information.

## Clutter and installation scale

Four visible groups is the hard comparison ceiling. Beyond four, ring growth,
pattern discrimination and legend scanning all deteriorate. The catalog itself
may contain any supported number of groups; only the spatial comparison is
limited.

At scale:

- rails use non-scaling strokes with a minimum rendered width and dark gap;
- non-member de-emphasis is the primary filter, not removal from the room;
- **Members only emphasis** may increase non-member muting, but retains faint
  Seat ghosts so spatial context and drag targets are not lost;
- names stay in the sidebar/tooltip rather than being stamped across the map;
- multiple elements repeat the same rails, but a selected Seat detail is the
  authoritative place to read its complete memberships;
- Point fields remain behind rails and Point handles remain operable above
  them. A future generic map-layer control may hide Point fields, but group
  inspection must not silently change authored Point state.

This overlay does not solve the existing map's general zoom or dense-Seat hit
target problem. Group delivery should verify representative dense layouts and
add a larger invisible hit target if Seat markers fall below touch size; a full
pan/zoom redesign should not be smuggled into this feature.

On iPad, the sidebar stacks below the map at the current responsive breakpoint.
The legend remains above the map; group rows and member checklists use full-width
touch rows. Map tap continues to select and pointer drag continues to position,
so no long-press or precision gesture is required for group inspection.

## Lifecycle behaviour

| State/change | Catalog and authoring | Spatial map | Live-control target |
| --- | --- | --- | --- |
| Empty group | Shows `0 Seats`; editable | Focus shows explicit empty message | Disabled with `No Seats` |
| Hidden group | Membership unchanged; eye off | No rail; still listed in selected Seat detail | Unaffected |
| Rename | Label updates; `gN` unchanged | Legend/tooltip update; slot retained | Label updates; target ID retained |
| Delete | Confirmation names member count; canonical deletion removes memberships | Focus/rail/legend removed atomically | Active target is invalidated to no target/no-send with notice; an explicit new choice is required |
| Seat added/removed | Both group and Seat checklists update | Focused/visible rails update | Member count and subsequent fan-out update |
| Seat unbound/offline | Still a member (groups contain Seats) | Rail remains; operational offline treatment remains | Still counted as canonical member |
| Group not visible | Still searchable/editable | No overlay | Still selectable if non-empty |

Deletion confirmation should read, for example, “Delete Front row (`g1`)? This
removes the group from 8 Seats. Seats and their parameter values are not
deleted.” A deleted active live target must fail closed to **no target/no-send**
rather than silently retaining a stale group selector or broadening scope to
All. The operator must make an explicit new target choice. All may only become
an automatic fallback if Bob separately ratifies that actuation risk during the
live-controls implementation review.

## Alternatives considered

### Recolour the Seat dot

Rejected. Dot fill already means element index, and one fill cannot express
overlap without blending or arbitrary priority.

### Pie wedges or segmented halos

Not recommended. Wedges avoid blending but change angle and apparent weight as
membership count changes; tiny wedges become unreadable at installation scale
and are poor touch/low-vision targets.

### Stacked coloured badges beside each Seat

Useful in a list, but rejected as the primary map encoding. Text/badges overlap
nearby Seats and Point handles quickly. The sidebar remains the detailed reader.

### Filled territorial hulls around group members

Rejected for version 1. Convex/concave hulls imply a continuous zone and can
include non-member Seats, especially with sparse or interleaved groups. Multiple
hulls also reproduce the misleading blended-colour problem.

### Only one group visible

Clear and simple, but insufficient for Bob's required overlap comparison.
Focus remains the default and compare is bounded to four.

### Persist an authored colour per group

Rejected for version 1. It expands the ratified data model, allows inaccessible
choices, and cannot guarantee distinct colours among arbitrary compared groups.

## Acceptance checks for delivery

The implementation stitch should include browser verification for:

1. focus one group; members are unmistakable and non-members remain locatable;
2. compare four groups; a Seat in all four shows four separate rails and no
   blended fill;
3. reject/show feedback for a fifth visible group without silently hiding one;
4. focus among compared groups, clear focus, then clear the full group view;
5. hover, keyboard focus and tap/selected-Seat detail expose identical names and
   tokens without depending on hover;
6. colour-blindness simulation plus monochrome/forced-colours inspection leaves
   rail order/pattern and legend mapping usable;
7. current Seat selected/offline/crashed/simulated styling and element-index
   colour remain legible above rails;
8. Point fields and handles remain legible and operable;
9. empty, hidden, renamed and deleted groups follow the lifecycle table;
10. group and Seat membership checklists update each other and never change
    merely from map focus/visibility;
11. 100-Seat representative venue at desktop and iPad widths, with overlapping
    groups and multi-element Seats;
12. touch targets measure at least 44 CSS px and no interaction requires hover;
13. the live-target picker shares display name, token, member count, empty and
    deletion behaviour without persisting visual slot/colour as identity;
14. every group row shows an open eye when visible and eye-off when hidden,
    while `aria-pressed` and action labels remain correct after every toggle;
15. the sidebar starts with Seats/roster/detail, Groups remains a subordinate
    disclosure after Seat detail, and a collapsed Groups summary still exposes
    active-overlay count without changing overlay state.

## Ratification record

Bob has ratified:

1. focus plus four-group comparison using separate concentric rails;
2. view-local comparison styles rather than authored/persisted colours;
3. checklist membership editing in both Seat and Group detail, with no direct
   map-paint mode in version 1;
4. empty groups editable/inspectable but disabled as live-control targets;
5. clear eye/eye-off iconography for group visibility;
6. the subordinate, collapsible Groups section after Seat roster/detail and
   before Simulation/Venue.
