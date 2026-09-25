# Playwright gotchas in the dashboard journeys

When writing or debugging a `tests/verify_*.py` browser journey, these are the traps earlier sessions fell into.

- Scope every selector to its host: component classes and `data-uid` repeat across tabs (Seats and Devices rosters both carry `.device-row[data-uid]`); use `#device-roster …`, `#show-root …`, `#control-column-host …`.
- Elements in an inactive tab never become visible — wait with `state="attached"` (also for `#ws-status`).
- Waiting for an element isn't waiting for its handler: heartbeats re-render and rebind. Wait on the binding of the **exact element you're about to click**, host-scoped.
- Heartbeat re-renders and CSS animation keep nodes "unstable": use one `page.evaluate` `scrollIntoView` and a fresh `bounding_box()`; gather all rects in one `evaluate`.
- `inner_text` applies `text-transform` — lowercase before matching.
- `wait_for_function(expr, arg=value)` — `arg` is keyword-only.
- One type-aware `page.on("dialog")` handler; two race.
- Persistence: use `page.reload()` (a fragment `goto` doesn't reload); `about:blank` has no `localStorage` — use `page.route` on a fabricated origin.
- A fixture without `control-panel.css` makes every metric `0px` and comparisons pass vacuously.
- Closed `<details>` contents still have `offsetParent`; use `is_visible()` or a `closest('details:not([open]) …')` check.
- A range input can't test focus-held render guards (pointer handling releases it); focus `input.live-gen-num`.
- SVG `getBoundingClientRect` ignores clipping — sample pixels, with the reference taken inside the same surface.
- The offline sweep takes 30 s; seat-row clicks must hit the `small` label, not the name input.
- A regression guard must not hang on the regression — bound every await.

## Triggers

- verify_
- playwright
- wait_for_function
- scrollIntoView

## Associations

- [[verification]]
- [[ws-snapshot-handlers]]
