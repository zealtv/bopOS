# show-lanes-and-scenes-design

**Status:** waiting — design session with Bob. Don't implement the grid or
change the show schema.
**Goal:** a reviewed model/UI brief for the next Show tab, using Ableton Session
View and QLab as references.

## Bob's working terms (to test and ratify)

- **step** — ordered playback unit
- **section** — span of steps between dividers
- **lane** — a column of steps; at most one active step per lane
- **scene** — a row across lanes, launched by one play control in a side gutter
- step follow actions run independently per lane (polyrhythmic sequencing);
  scenes have their own follow actions

Don't retrofit CSS columns onto today's flat `items` array.

## Brief must cover

1. Lane/scene identity and order, sparse cells, dividers across lanes, migrating
   existing shows into lane 0.
2. Scene launch timing; what empty destination cells do (stop / keep / replace).
3. Which wins when a lane follow and scene follow arrive together.
4. goto/next/previous scope, independent playheads, pause/stop-all, step
   `then_actions` vs scene follows.
5. Editing: add/remove/reorder lanes and scenes, drag/drop, selection and
   inspector, narrow screens, the edit bar.
6. Desktop/tablet wireframe with accessible scene launch and clear
   playing/armed/follow state.

Include DECISION and OPEN QUESTION lists. Tie only after Bob ratifies terms,
schema, launch-conflict rules and follow ownership. Language syntax stays in
`scene-language-spec`.
