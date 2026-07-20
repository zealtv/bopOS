# Show chrome & density braindump

Bob's 2026-07-20 reaction to the tied `01-layout-review` wireframe — the
schematic mockup's density and chrome read better than the shipped Show tab
in several ways, and he wants those qualities integrated (perhaps app-wide).
Authorizes the `18-show-chrome-density` thread.

## Source

Bob, 2026-07-20, immediately after the `show-layout-polish` thread tied
(edit bar, inline step name, responsive OSC terminals). Verbatim text in
`content/braindump-2026-07-20.md`.

## What he liked in the mockup

- Bounded step list.
- Buttons wrapping tightly around their text; sharper corners; overall
  denser UI.
- Named dividers — dividers mark sections, so sections should be nameable —
  and the divider styling with lines either side of the name.
- Steps reading as collapsible (fold up to hide the message pills).

## Pain point

The message inspector growing taller pushes the OSC terminals out of view.
The inspector should own its space: a collapsible sidebar, popped out while
building the show, hidden during a show to free real estate.

## Rulings

- Desktop-first app, except the facilitator tab (tablet first, then
  laptop/phone). Current mobile sizing is generally fine.
- Collapsible-step row anatomy (collapse indicator vs grab bar vs play
  button vs alias) needs an expert UI/UX review before implementation; the
  current ⋮⋮ grab-bar icon must be retained.
- "Perhaps the app style broadly" — scope of the chrome changes
  (Show-tab-only vs app-wide) is an open question for the review to weigh
  and Bob to ratify.

## Status

Laid out on the loom as `18-show-chrome-density` (UX review gate first, then
implementation children). Not yet ratified beyond the thread layout itself.
