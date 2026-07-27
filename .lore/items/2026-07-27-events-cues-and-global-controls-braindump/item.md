# Events/cues unification + global-controls home braindump

Bob's second 2026-07-27 braindump, following the control-panel mockup session
(lore `2026-07-27-control-panel-ui-and-architecture-braindump`). Four calls:

1. **Cues are zero-element events.** Cue triggering belongs *on the control
   panel* (targetable at all seats, a group, or an individual seat), not on a
   separate surface. Events have 0, 1, 2, or 3 float elements (0 = cue;
   1/2/3 = e.g. MIDI note / +velocity / +duration — "really these could be
   anything that just floats"). This may be deeper than adding a new
   `<target>/e/*` plane: cues may be **absorbed into the event plane**. The
   `44-event-plane` design stitch must answer this.
2. **Control panel sections.** The control panel gets a *parameters* section
   and an *events* section — no intermingling for now (easier, and keeps the
   Patch-tab manifest construction area less changed).
3. **Global controls get a new home.** Master fader, mute, and cue lead time
   are now recognizably *global* controls. Candidate homes: persistent in the
   top menu bar, or their own panel in the Monitor dock. Bob's call: **try
   the Monitor panel first**. Lead time remains a global control positioned
   with the master fader.
4. **Manifest reordering.** In the Patch tab's manifest editor, parameters
   (and eventually events) should be drag-reorderable, so the operator can
   reorder the control panel.

Plus a note to dwell on, not act on: **"Monitor" terminology may want
revisiting down the line** — the dock will likely gain a seat map and other
visualizations. Monitor is fine for the moment.

## Source

Chat session 2026-07-27 (same day as the mockup braindump; Bob flagged it
"might subsume or inform other stitches"). `content/braindump.md` holds the
message verbatim.
