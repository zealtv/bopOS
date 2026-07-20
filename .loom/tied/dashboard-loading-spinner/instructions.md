# dashboard-loading-spinner — a spinner that bops

**Goal:** the dashboard shows a loading signifier from first paint until it
is actually ready, instead of the current blank/partial delay.

Bob, 2026-07-19: "There's a little bit of a delay when bopOS loads, so I'd
like some sort of loading signifier as the page loads and is getting
ready. I'd like a cool spinner that 'bops'."

## Scope

- Full-page overlay (or centered stage) visible immediately on load —
  inline in the HTML/CSS so it renders before any JS/WS work, not gated
  behind the app bundle.
- Dismiss when the app is genuinely ready: first WebSocket `state`
  message applied (not merely DOMContentLoaded). If the WS drops later,
  reuse whatever reconnect indication already exists — this stitch is
  about initial load, don't invent a second disconnect UI.
- The spinner should *bop*: a rhythmic pulse/bounce in the dashboard's
  existing visual language (CSS animation, no assets, respects
  `prefers-reduced-motion`). This is user-facing — pick one tasteful
  design, screenshot it, and let Bob veto in review rather than gating
  up front (small enough to redo).

## Verify

Playwright verify (house pattern): dashboard + simfleet on non-default
ports; assert the spinner element is present before the WS state arrives
(throttle or delay the connection), disappears after first state, and
never reappears in steady state. Screenshot the spinner for review.
