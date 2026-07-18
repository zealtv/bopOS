# 7-osc-consoles worklog — 2026-07-18

Outgoing/incoming OSC consoles on the Show tab, per design note §3 end.

## Backend (`dashboard/osc_bridge.py`)

Two always-on taps, no subscribe verb: `OSCBridge.send()` broadcasts
`osc_out {ts, address, args, target}` (every datagram the dashboard sends,
any tab — set_param/fire_cue/points all funnel through `send`), and
`handle()` broadcasts `osc_in {ts, address, args, source}` (everything on
the LAN receive side, heartbeats included). Args are coerced JSON-safe;
both taps guard `RuntimeError` because sends can happen before the asyncio
loop exists. The server does no filtering.

## Frontend (`static/js/show.js`, `static/css/style.css`)

Consoles live in a `#show-consoles` container *outside* `#show-root`, so
the high-rate stream never re-renders the show table and show-state renders
never wipe console DOM. Two collapsed-by-default `<details>` panels
(Outgoing/Incoming), each with a filter box, Pause/Resume, Clear, and a
monospace log.

- Client-side ring buffer: 500 entries kept, newest 200 rendered, lines
  pre-formatted at push time; renders batch through one 150 ms timer and
  write `textContent` once — heartbeat floods cost one string join per
  flush, not per-message DOM churn. A "N shown · M seen" counter sits in
  the summary.
- Filter: space-separated terms AND together, `*` wildcards, `!` negation,
  case-insensitive, applied live and client-side over the buffer
  (e.g. `/p/* !/sync`).
- Auto-scroll sticks to the newest line and pauses when the user scrolls
  up (resumes when they return within 24 px of the bottom). Pause freezes
  the view while buffering continues; Clear resets entries and the seen
  counter.

## Verify

`verify_show_consoles.py` (this dir), 10 checks, **0 failures**: consoles
render collapsed; the triggered step's `/all/p/gain` send appears with args
and destination; simfleet `/sync/pong`+heartbeat traffic appears with a
source; `/all/p/*` narrows the outgoing view; `!/sync*` hides sync noise
while keeping other lines; pause freezes under live traffic and resume
catches up; clear empties and live traffic refills; no page errors.
Screenshot: `consoles.png`. Re-ran all seven tied show-thread verifies
(2, 3, 4, 5, 5b, 5c, 6): green, no amendments needed.
