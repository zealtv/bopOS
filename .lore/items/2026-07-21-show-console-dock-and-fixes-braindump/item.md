# Show console dock, chrome fixes, theme tint & listener range braindump

Bob's 2026-07-21 fix list after living with the tied `18-show-chrome-density`
work. One headline feature (a VS Code-style bottom console dock), four small
Show-tab defects, an app-wide light-theme tint shift, and one genuine design
challenge on the Seats listener widget. Authorizes threads `19-show-chrome-fixes`,
`20-console-dock`, `21-theme-cyan-tint`, and `22-listener-range-ux`.

## Source

Bob, 2026-07-21, in the autopilot session immediately after `18-show-chrome-density`
stitches `02`/`04`/`05` tied. Verbatim text in `content/braindump-2026-07-21.md`.

## What he asked for

**Console dock (the headline).** The outgoing and incoming OSC terminals should
collapse and expand *together* — one window, one frame. That frame should grow
into a VS Code-style bottom console with tabs: incoming OSC, outgoing OSC, a
terminal for *typing and sending* OSC messages, and possibly a system-overview /
utility tab. Naming left to the implementer. Narrow view: tabs on a single panel.
Wide view: tabs draggable to either side so they snap into a split — "think
console tabs in VS Code." A **map view** tab (seats from above, point positions,
spatial automation state — a composition overview monitor) is explicitly wanted
*later*; not to be implemented now, but the dock should have room for it.

**Show-tab defects.**
- Narrow view: the expanded inspector's collapse button overlaps the edit bar's
  delete button.
- Narrow toolbar iconography: divider is `—` and step is `+`, which reads as
  add-step / remove-step. Both need better icons.
- Divider rows: the rules either side of the title should be *short lines*, not
  full-width — as in the `01-layout-review` prototype screenshot. Untitled
  dividers should drop the gradient entirely (the grab handle made it redundant)
  and render as a plain blank line.
- Message inspector, LFO parameter: the period-duration number box is obscured by
  its increment/decrement buttons. Shrink the unit box to make room.

**Theme.** The light theme's green tint (e.g. named steps) should shift toward
cyan — the palette should read purple-and-cyan, not purple-and-green.

**Listener range (design challenge).** On Seats, the listener range is currently
set by dragging the knobbly heading line outward; when the listener sits near a
map edge, the line clips and the range can't be extended. Bob wants the range
interaction constrained to the listener dot itself, and the range indicated some
other way — a gradient, a thin outline circle, or similar — showing maximum range.
Explicitly flagged as "a bit of a design challenge... one to put to a UX/UI expert
to ideate on."

## Status

Laid out on the loom as four threads (see above). The console dock and the small
fixes are authorized to implement; the listener range is a design gate — proposal
first, Bob ratifies, then implementation. The map tab is deferred by name.
