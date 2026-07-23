# 20-console-dock

**Monitor v1 complete, 2026-07-23.** The ratified Incoming, Outgoing, Send,
Reports, System, persistence, and wide split/snap slices are tied. A follow-up
also removes the visible `shown` / `seen` traffic-count copy. Only the
deliberately deferred future Map tab remains waiting.

Grow the Show tab's two independent OSC `<details>` consoles into a single
VS Code-style dock at the bottom of the app: one frame, tabbed views, and — at
wide widths — tabs draggable to either side of the frame to snap into a split.

Authorized by lore item `2026-07-21-show-console-dock-and-fixes-braindump`
(verbatim braindump in its `content/`). Bob, in his words:

> I'd like the terminals to collapse and expand together, so they're essentially
> one window... That might in fact become a kind of console down the bottom, a
> little bit like VS Code with different tabs for incoming OSC, outgoing OSC, and
> maybe some sort of terminal that lets us send OSC messages by typing them, as
> well as perhaps some other like system utility stuff... In a narrow view, each
> of those views could be a tab on a single panel, but in a wider view, we should
> be able to drag those tabs either side so that they snap to the sides of that
> wider panel. Think console tabs in VS Code.

The name of the thing is left to the implementer (Bob: "I'd leave the name up to
you") — pick one in `01-dock-design` and use it consistently in code, UI copy,
and docs.

## Order of work

1. `01-dock-design` — **ratified 2026-07-23.** The app-wide surface is named
   Monitor and ships Incoming, Outgoing, Send, Reports, and System in v1.
2. `02-unified-frame` — Bob's actual complaint: the two OSC consoles become one
   collapsible frame with two tabs. This is the shippable slice on its own.
3. `03-osc-send-tab`, `04-reports-tab`, `05-system-tab`,
   `06-wide-split-snap` — the remaining ratified v1 tabs and layout.
4. `07-map-tab.waiting` — explicitly deferred by Bob; a placeholder so the dock
   is designed with room for it.

## Constraints carried in from the shipped consoles

- The consoles deliberately live **outside `#show-root`** so the high-rate
  `osc_in`/`osc_out` stream never re-renders the show table and show renders
  never wipe the console DOM (see the comment above `show-consoles` in
  `dashboard/static/js/show.js`). Whatever the dock becomes, preserve that
  separation — this is a performance property, not an accident.
- Client-side filtering per view and the bounded scrollback stay.
- Self-contained app: no CDN, no icon fonts, no new runtime dependency.
- Desktop-first, except the facilitator tab (which is out of scope here).

## Ratified scope

Monitor is app-wide (the standalone facilitator page remains excluded), lives
outside all tab panels and `#show-root`, persists layout in browser
`localStorage`, and does not auto-collapse when playback begins. See the tied
`01-dock-design/decisions.md`.
