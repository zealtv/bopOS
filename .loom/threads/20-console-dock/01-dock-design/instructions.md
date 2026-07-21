# 01-dock-design

Design the console dock. Produce a written proposal, surface it to Bob, mark
this stitch `.waiting` for ratification, then tie it with the ratified design as
the stitch artifact (`decisions.md`) — the pattern used by
`16-param-automation/automation-4` and the seat-group design stitches.

## Decide

- **Name.** Bob left it to us. One word or two, used in code (`#…`, CSS prefix),
  UI copy, and docs. Avoid "console" colliding with the browser console in
  agent-facing docs if that gets confusing.
- **Tab set at v1** and the reserved future tabs: incoming OSC, outgoing OSC, an
  OSC send terminal, a system/utility overview, and (deferred) a map view. Say
  which ship when.
- **Collapse model.** One frame, one collapse control, remembered across
  reloads? Height draggable? What does "hidden while running a show" look like —
  the `18-show-chrome-density` braindump wanted real estate back during a show.
- **Narrow vs wide.** Narrow: one panel, tabs across the top. Wide: tabs
  draggable to either side and snapping into a split. Define the breakpoint, the
  drag affordance, the drop targets, what happens when both sides are occupied,
  and whether the split ratio is draggable and persisted.
- **IA placement / scope** — the open question in the parent: Show-tab-only vs
  app-wide. Recommend one.
- **Persistence.** Where does dock layout state live — `localStorage` (client
  preference, like the theme toggle) or server-side show/installation state?
  Prefer client-local unless there's a reason it must follow the installation.
- **The map tab's requirements**, at the level of "does this design leave room
  for a live spatial view" — no implementation.

## Constraints

Everything in the parent's "Constraints carried in from the shipped consoles",
particularly keeping the dock DOM outside `#show-root`.

## Deliverable

`decisions.md` in this stitch, plus a lore item if the proposal is substantial
enough to want the whole artifact kept. Update the parent's instructions with
the ratified scope call, and un-`.waiting` the children the design unlocks.
