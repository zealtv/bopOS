# Monitor dock — design proposal

Status: **ratified by Bob, 2026-07-23.** No UI implementation had started when
this decision was accepted.

## Recommendation

Name the app-wide bottom surface **Monitor**. Use `monitor-*` for CSS classes,
`#monitor-dock` for the frame, and “Monitor” in UI copy. It describes traffic,
reports, system state, and the future spatial view without colliding with the
browser console or implying that every tab is a command terminal.

Ship these tabs in v1:

1. **Incoming** — the existing bounded, filterable `osc_in` stream.
2. **Outgoing** — the existing bounded, filterable `osc_out` stream.
3. **Send** — typed OSC with validation, session history, and an echo into
   Outgoing.
4. **Reports** — demand inspection of patch-authored `/report` values.
5. **System** — read-only WebSocket/fleet/clock/show/patch summary from state
   already held by the Dashboard.

Reserve **Map** as a future tab. Do not ship a disabled placeholder; the tab
registry and layout state must accept it later without changing the frame.

## Why Reports is a distinct tab

`to-bopos-report` is a Pure Data-local send bus, not Dashboard traffic. In
`pd/bopos~.pd` it is formatted as `/report <name> <values…>` and sent to local
`bopos.py` on UDP 7770. `bopos.py` retains only the latest typed values for each
name in memory. It does not forward that write to the Dashboard, so the write
does not appear in today's Incoming or Outgoing OSC consoles or in the Device
Report section.

The contract exposes those retained values only by a one-shot
`/<id>/os/probe <name>` request, answered as
`/os/probe <id> <name> <values…>`. The raw request and reply belong in
Outgoing and Incoming respectively, but making users construct that exchange
by hand is not a usable inspection surface.

The Reports tab therefore has:

- an assigned physical Device/Seat target picker;
- a report-name field and **Request** button;
- the last returned typed values, device identity, and receipt time;
- session-only request history;
- explicit empty/timeout/unknown states;
- no subscription and no polling.

This preserves the demand-driven contract. Because the current probe selector
is Seat/id-based, unassigned Devices are shown but unavailable with a terse
explanation; v1 does not expand the OSC contract merely to inspect an
unassigned patch. A response also remains visible as raw traffic in Incoming.
Node restart clears retained report values; the UI must not imply persistence.

## Placement and lifecycle

Make Monitor app-wide, after `.tab-stage` and outside every tab panel,
especially outside `#show-root`. Its data owners must not be recreated by Show
renders or tab changes. Move the current console code out of `show.js` into a
small app-level module rather than leaving an app-wide surface owned by Show.

The app-wide call follows from the contents: Incoming, Outgoing, Reports, and
System remain useful on Devices, Patches, Seats, and Assets. The standalone
facilitator page remains excluded.

One frame has one collapse button. Expanded height defaults to 320 px and is
drag-resizable from 180 px to 55 viewport-height. Collapsed state is a compact
header/tab rail, not `display:none`: unread counts and connection state remain
visible while reclaiming the show workspace. Starting playback does not
silently change the operator's layout; a running show uses the same one-action
collapse.

## Narrow and wide layout

Use the Monitor container width, not the browser width:

- below 1000 px: one pane and one horizontally scrollable tab strip;
- at or above 1000 px: tabs expose a drag handle and left/right drop targets.

A wide drop on the empty side creates a 50/50 split. Dropping onto an occupied
side appends the tab there and activates it. Moving the final tab out of a pane
removes that pane. An aborted drag changes nothing. The split divider is
draggable and clamped to 30/70 through 70/30.

The keyboard equivalent is a tab action menu with **Move left**, **Move
right**, and **Return to one pane**. Narrow mode does not destroy the saved wide
arrangement: it presents all tabs in canonical order, then restores the wide
layout when space returns.

## Persistence

Store layout preference in browser `localStorage` under a versioned key such
as `bopos.monitor.v1`:

- open/collapsed;
- expanded height;
- wide tab-to-pane assignment and active tab per pane;
- split ratio.

Validate every loaded field and fall back independently when stale. Do not put
layout preferences into show or installation state. Traffic buffers, filter
text, Send history, and report results are session-only and are not persisted.

## Rendering and accessibility

- Keep the existing 500-entry bounded buffers, 200-line render window,
  per-stream filter, pause, clear, and 150 ms batched rendering.
- A tab is a real `role=tab`; panes are `tabpanel`s; collapse and resize have
  labelled keyboard controls.
- Announce Send errors and Report outcomes, not high-rate traffic.
- Keep the self-contained app rule: no dependency, icon font, or CDN.
- Focus/drop/split state must be visible in both themes without colour as the
  sole signal.

## Delivery slices after ratification

1. Unified app-level frame with Incoming/Outgoing and persistence.
2. Send tab and its narrow server route.
3. Reports tab using one-shot `/os/probe`.
4. System tab using existing WebSocket state only.
5. Wide split/snap and keyboard equivalent.
6. Map remains waiting on spatial/scene design.

## Ratification

Bob accepted:

- **Monitor** as the name;
- app-wide placement;
- Reports as a first-class v1 tab;
- System in v1 rather than deferred;
- 1000 px container breakpoint and 30/70 split limits;
- no automatic collapse when playback begins.
