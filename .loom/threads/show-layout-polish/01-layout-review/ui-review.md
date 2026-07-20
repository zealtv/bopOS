# UI designer review — Show layout polish

Reviewed against the current Show implementation and retained wide screenshot,
using Ableton Live and QLab as conceptual references.

## Recommended shape

- Put one persistent toolbar immediately above `.show-rows-box`, inside
  `.show-list-shell`. Group Add Step/Add Divider at the left, leave a flexible
  centre for later lane controls, and place Duplicate/Delete at the right.
  Keep action positions stable and disable unavailable actions instead of
  hiding them. Use icon plus short text when space permits and icon-only below
  the narrow breakpoint, always with `aria-label`, tooltip, visible focus, and
  an expanded touch target.
- Addition should be relative to the selected structural row, appending when
  nothing is selected. A message focus makes Duplicate/Delete ambiguous; Bob
  should ratify whether the bar targets that message, its enclosing step, or is
  disabled. Cloning a step must mint fresh UIDs for the step and every message.
- Remove the bottom add bar and inspector Arrange section only after the new bar
  has parity for empty shows, insertion, deletion, undo, keyboard editing,
  drag/reorder, scroll-to-new-row, persistence, and second-client updates.
- In the Step inspector, render the authored step name as the bold title. Click
  or tap swaps it for one selected single-line input; Enter/blur commits,
  Escape restores, and blank returns to `Untitled step`. Keep `alias` internal
  for compatibility and do not save every keystroke.
- Place OSC terminals in two equal columns while each remains readable, likely
  until about 900px. Expanded terminals use equal fixed heights; summary and
  controls stay fixed while logs scroll independently. Stack outgoing then
  incoming on narrower displays. Long frames must never widen the page.

## Lanes/scenes warning

The future grid is not a layout-only change. The current show is one flat
ordered `items` array and playback allows one active step globally. Multiple
lanes require durable lane/scene identity, sparse cells, migration, independent
playheads, and a rule for conflicts between lane and scene follow actions. The
largest UX decision is what a scene launch does to a currently playing lane
when the destination scene has no step in that lane. Resolve this in the
Bob-gated sequencing design stitch before implementation.

## Review checks

- 1280px desktop, tablet, and 768px narrow; light and dark themes.
- No page-level horizontal scroll and no toolbar movement during list scrolling.
- Selection target is unmistakable before Duplicate/Delete.
- OSC traffic cannot change terminal height; filters, pause, clear, counts,
  collapse, and auto-scroll remain independent.
- Inline name edit covers pointer, touch, Enter, blur, Escape, blank, persisted
  reload, and second-client refresh.
