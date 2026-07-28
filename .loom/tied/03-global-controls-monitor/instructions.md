# 03-global-controls-monitor

Give the three now-recognizably-global controls — **master fader**, **MUTE
ALL**, and **cue lead time** — a shared home, starting with **a panel in the
Monitor dock**. Source: Bob's 2026-07-27 second braindump (lore
`2026-07-27-events-cues-and-global-controls-braindump`). Bob considered two
homes (persistent top menu bar vs a Monitor panel) and ruled: "let's try
putting them in the monitor panel to start with" — so this is a ratified
direction to implement and then review live, not a design gate.

Where they live today:

- master fader: app header (`dashboard/static/index.html` `#master-control`,
  handlers in `dashboard/static/js/dashboard.js`);
- MUTE ALL: app header (`#mute-all`);
- cue lead time: Show-tab transport (`dashboard/static/js/show.js`
  `#show-cue-lead`).

Scope:

- A Monitor-dock panel (alongside Incoming/Outgoing/Send/Reports/System)
  holding the three controls; lead time is positioned with the master fader.
  Behavior/wire semantics unchanged — this is relocation, not redesign.
  MUTE ALL keeps its execution semantics and danger affordance; consider
  what, if anything, remains visible when the dock is collapsed (a muted
  state must never be invisible — output safety).
- Remove the old header/Show-transport placements once the new home works
  (Show tab may keep a read-only lead-time indication if losing it hurts —
  use judgment, note the call in `decisions.md`).
- Follow the Monitor persistence pattern for which panel is selected; styles
  in the compact `--chrome-*`/control-panel token language.

Record, don't act on: Bob notes the **"Monitor" name may want revisiting**
down the line — the dock will likely gain a seat map and other
visualizations. Monitor stays for now; carry the note into `decisions.md` so
a future naming pass finds it.

Ordering: after the current control-panel implementation children; touches
the same chrome, so coordinate with `02-app-wide-rollout-design` rather than
racing it. Cue-triggering-from-the-control-panel is **not** this stitch —
that lands with `44-event-plane`.

Verify: living Playwright journey — controls present and functional in the
Monitor panel, absent from header/Show transport, mute state visibility with
the dock collapsed.
