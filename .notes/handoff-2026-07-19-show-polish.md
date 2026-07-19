# Handoff — 2026-07-19: 15-show-polish laid out, ready to work

## State of play

- `14-show-tab` is fully tied, including this session's `6b-show-management`
  (show create/switch/rename/delete in the transport strip; `rename_show`
  WS handler; verify + full tied-sweep green at `5a5930e`).
- Bob's 2026-07-19 braindump is kept verbatim in lore:
  `.lore/items/2026-07-19-show-tab-polish-braindump/`. It authorizes the
  **`15-show-polish`** thread, laid out on the loom in sequence of attack:

  1. `p1-zero-value-and-transport-bugs` — **start here.**
  2. `p2-exclusive-playback-and-progress`
  3. `p3-global-transport-and-cue-lead`
  4. `p4-step-list-scrollbox`
  5. `p5-inspector-defaults`
  6. `p6-drag-and-keyboard-editing` (biggest; split permission granted)
  7. `p7-patch-tab-tidy` (independent — claimable alongside p1–p6)
  8. `p8-docs-and-handoff`

  Each stitch's instructions.md carries scope, investigation leads, and
  the verify plan. Thread-level rulings (exclusive playback, forward-sync
  retirement, keyboard+drag editing, Patch tab copy) are in the thread
  instructions — read those first.

## Leads the next session should not re-derive

- **p1 zero-value bug:** falsy `||` chains in `show.js` message builder
  (`renderParamBuilder`: `argValue(...) || declaration.default || ""`);
  audit all value chains for legitimate 0.
- **p1 lost clicks:** row re-render on every broadcast means a click can
  hit a stale-verb button; fix by sending intended verb / idempotent verb
  mapping engine-side, then prove with rapid play→stop.
- **p3 lead time:** `fire_cue(cue_id, lead_ms=500)` in `osc_bridge.py`
  already parameterizes the horizon; the stitch pipes a persisted setting
  into it. Wire shape (§3.1) unchanged.
- **p5/p6:** backend ops (`move_message`, `move_item`, empty
  `then_actions` ≡ stop) already exist — these are authoring-surface
  changes plus the undo design (client-local snapshot stack +
  `apply_show` full-document op is the sketched shape; design in worklog
  before coding).
- Amending tied 14-show-tab verifies as the UI moves is expected — log
  every amendment (5b/5c precedent).

## Verify infrastructure

House pattern unchanged: `~/.venvs/bopos/bin/python <verify>.py`, real
`dashboard/server.py` + `tools/simfleet.py` on random loopback ports,
headless Chromium, repo by marker, one type-aware dialog handler. Copy
`.loom/tied/6b-show-management/verify_show_management.py` as the newest
template (includes a server-restart pattern past the 1 s debounced state
save).

## Also open on the loom (not this sweep)

`dashboard-loading-spinner`, `live-param-catchup`,
`notify-patch-lifecycle`; `patch-workflow-friction` resumes after
15-show-polish (host-loom loose end has the framing — see
`.notes/handoff-2026-07-18-show-tab.md`).
