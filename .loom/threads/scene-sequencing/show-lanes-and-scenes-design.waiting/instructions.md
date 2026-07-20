# show-lanes-and-scenes-design

**Design-only, Bob-gated. Do not implement the grid or alter the schema.**

Hold a brief design session and review the next Show model using Ableton Live's
Session View and QLab's cue-list clarity as references. Bob's working
terminology and behavior are:

- **steps** are ordered playback units;
- **sections** are spans of steps delimited by dividers;
- **lanes** are sequential columns of steps, with at most one active step per
  lane;
- a horizontal row across lanes is a **scene**, launched by one play control in
  a fixed side gutter;
- step follow actions operate independently within each lane, enabling
  decoupled/polyrhythmic sequencing; and
- scene launching has its own distinct follow actions.

Treat these as the proposal to test and ratify, not permission to retrofit CSS
columns onto the current flat `items` array. Produce a reviewed model/UI brief
covering:

1. durable lane and scene identity/order, sparse cells, dividers/sections across
   lanes, and migration of existing shows into lane 0;
2. scene launch timing and the rule for empty destination cells (stop, preserve,
   or replace current lane playback);
3. arbitration between a lane follow and a scene follow arriving together;
4. goto/next/previous scope, independent lane playheads, pause/stop-all, and the
   separation of existing step `then_actions` from scene follow actions;
5. add/remove/reorder lane and scene editing, drag/drop, selection/inspector
   ownership, narrow-screen navigation, and the extensible edit bar's role; and
6. a desktop/tablet wireframe with accessible scene launch controls and clear
   playing/armed/follow state.

Record explicit DECISION and OPEN QUESTION lists for Bob. This stitch can only
be tied after Bob ratifies the terminology, schema, launch-conflict rules, and
follow-action ownership. Language syntax and scripted scene work remain in the
separate `scene-language-spec.waiting` child.
