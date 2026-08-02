# Implementation decisions

- `GroupSlots` is the one JavaScript authority for the four Seats-map colours
  and patterns. It also exposes those colours as CSS custom properties, so the
  target picker and card borders no longer carry divergent literals.
- The desktop Seats map writes its four current presentation slots to
  `bopos.group.slots`. A same-document event refreshes Control immediately;
  the normal cross-document storage event refreshes Remote.
- Slot assignment remains presentation state, not installation/group data.
  An unassigned group gets the neutral `.target-card` face.
- `.target-card` is a small shared component root used by Control's outer card
  and Remote's individual `.live-card`. This keeps ownership explicit while
  giving both hosts exactly the same All/group/neutral border treatment.
- The All face is 3px white with the map's `#071015` backing keyline. Slot 4
  uses the existing Seats-tab double-border equivalent to the SVG dash-dot.
