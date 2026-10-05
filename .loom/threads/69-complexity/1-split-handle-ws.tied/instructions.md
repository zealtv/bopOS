# 1-split-handle-ws

**Status:** waits on `65-remove-presets/2-remove-presets` and
`68-remove-git-patch-route`
**Goal:** `Dashboard.handle_ws` becomes a short dispatcher over small,
individually readable handlers.

## Today

`dashboard/server.py:356` — 1,093 lines, 89 `elif kind ==` branches. Locking is
done by re-calling itself with `supervisor_locked=True` /
`manifest_locked=True`, and two big sets (`serialized_mutations`,
`edit_blocked_mutations`) must be kept in step with the branches by hand.

## Shape (yours to refine)

- A table from message type → handler, with each handler's needs declared
  beside it (takes the supervisor lock, blocked during Patch edit,
  editor-scoped allowed) instead of in separate sets.
- Group handlers by area — seats/groups, devices, distribution, shows,
  supervisor, editor — possibly in separate modules. `server.py` is 3,321
  lines; it doesn't need to stay one file.
- Delete orphan verbs found by the review rather than porting them (see
  `70-dead-code-sweep/1-dead-code`).

## Done when

- No handler over ~60 lines; the dispatcher is readable on one screen.
- A test that every message type the frontend sends has a handler, and every
  handler is reachable (the review's diff, made permanent).
- Fast + browser green; no behaviour change.
