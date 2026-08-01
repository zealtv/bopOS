# Task: Show-tab global transport, forward-sync retirement, global cue lead

Repo: /Users/bob/repos/bopOS. Files: `dashboard/show_engine.py`,
`dashboard/show_model.py`, `dashboard/server.py`, `dashboard/osc_bridge.py`,
`dashboard/static/js/show.js`, `dashboard/static/js/facilitator.js` (one
small change), `dashboard/static/css/style.css`,
`.notes/show-tab-design-2026-07-18.md` (amendment section), one new verify
script. Never touch `.pd` files or `.loom` state (write only into the stitch
directory named below).

## Background

p2 made playback exclusive: at most one step is playing or paused, and
`show_playback` carries `{"steps": map, "armed": uid|null}`. The transport
strip (`renderTransport` in show.js) holds the show-manage cluster, the
playing indicator, and a text "Stop all" button. Steps currently carry a
`forward_sync` flag choosing `bridge.fire_cue(cue_id)` (scheduled ~500 ms
ahead on the synced clock) vs `fire_cue_now`. `OSCBridge.fire_cue(cue_id,
lead_ms=500)` already clamps lead to 100..10000. The facilitator surface has
its own per-fire `#cue-lead` input (facilitator.js ~185).

## Change 1 — global transport controls

Add three icon buttons to the transport strip's actions cluster (before the
playing indicator): **play/pause**, **stop**, **next**, using the existing
`iconButton`/glyph classes from the step rows (play, pause, stop, next
glyphs are already drawn; reuse, don't redraw).

Behavior (all through the existing WS transport verbs; the active step is
the single playing-or-paused uid in `playback.steps`):

- **Play/pause**: no active step → `step_start` on the focused step — the
  focused step row, or the step containing the focused message — falling
  back to the first step in the document. A playing step → `step_pause`; a
  paused step → `step_resume`. The glyph reflects the action it will take
  (play triangle when it would start/resume, pause bars while playing).
- **Stop**: `step_stop` on the active step; disabled-looking no-op when
  nothing is active.
- **Next**: `step_trigger_next` on the active step (playing or paused);
  hidden or visibly disabled when nothing is active (match how the strip
  reads best at 5b density; keep the header-height budget — compact 30px
  controls with the ::after expanded hit area idiom used by `.show-manage
  button`).
- **Stop all** keeps its behavior and danger styling but its text label
  becomes the stop glyph (keep an aria-label/title "Stop all steps").
- Route the clicks through `sendTransport` so p1's optimistic rendering
  covers the global buttons too.

## Change 2 — forward-sync retirement (all cues forward-sync)

- `show_engine._send_message`: `/cue` messages always use
  `bridge.fire_cue(cue_id, lead_ms=<global lead, change 3>)`. Remove the
  `forward_sync` parameter threading (`_emit_messages` included) and the
  docstring's two-path description. `fire_cue_now` itself stays (other
  surfaces use it).
- show.js: remove the `#show-forward-sync` tick box and the mixed-sync
  hint (`hasMixedForwardSync`, `syncHint`) from the step inspector; remove
  the `forward_sync` change handler.
- `show_model.clean_step`: accept and **drop** a stored `forward_sync` key
  — legacy show files load, saves never write the key. Update the server's
  update_step allowed-field tuple (server.py ~1087) to stop accepting it.
- `.notes/show-tab-design-2026-07-18.md`: append a short dated amendment
  section (do not rewrite the note) recording: all cues forward-sync, the
  per-step flag is retired, the lead is a global setting.

## Change 3 — global cue lead time

A persisted installation-level setting (not per-show): `cue_lead_ms`,
default 500, clamped 100..10000.

- **Server**: store it in the installation state dict (follow how existing
  installation-level settings are persisted/broadcast in server.py /
  state.py — find one, e.g. the fleet-safety/master fields, and copy the
  pattern exactly). New WS message `set_cue_lead {ms}` validates, clamps,
  persists (debounced state save like its siblings), and broadcasts so all
  clients agree.
- **Engine path**: show playback's `fire_cue` calls pass
  `lead_ms=<current setting>`. Thread it the way the engine already gets
  its dependencies (constructor callable or a small accessor set by
  server.py — pick the least invasive; the engine must read the *current*
  value at fire time, not a construction-time copy).
- **Show tab UI**: a compact labelled numeric input ("cue lead · ms", min
  100, max 10000, step 50) in the transport strip actions cluster, next to
  the new transport buttons — transport policy lives with the transport
  controls, not with the diagnostic consoles (this placement decision is
  settled; note it in your report). Change on commit (change event), value
  reflects broadcasts, and while the input is focused a broadcast must not
  clobber the operator's typing (the render() uncommitted-pick guard for
  the shows dropdown is the precedent — mirror the idea if needed).
- **Facilitator**: initialize/refresh its `#cue-lead` input default from
  the broadcast setting instead of the hardcoded 500 when the operator has
  not modified it this session; its per-fire override behavior stays.

## Verify script (new)

`.loom/threads/15-show-polish/p3-global-transport-and-cue-lead.stitching/verify_show_transport.py`
— house pattern (copy the harness shape from
`.loom/tied/p2-exclusive-playback-and-progress/verify_show_exclusive.py`):
repo root by marker, random loopback ports, real server + simfleet,
headless Chromium, single type-aware dialog handler, teardown, `check()`
lines, exit 1 on failure. Fixture: at least two steps; step A includes a
`/cue` message with a declared cue id; a legacy show JSON containing
`"forward_sync": true` on one step and `false` on another.

Checks:

1. Global play with nothing focused starts the first step; global stop
   stops it.
2. Focus step B's row; global play starts B (not A). Pause → the same
   button resumes. (Assert engine state via the playing indicator and row
   classes.)
3. Global next on a playing step triggers its then-action now.
4. Stop-all renders as a glyph button (no visible text) and still stops.
5. Cue lead: set the input to a distinct value (e.g. 1200); fire step A
   (its `/cue` message goes out via the sync plane): capture the LAN
   `/cue <id> <sharedTimeNs>` datagram (the verify can bind the fleet
   side itself or read simfleet's log) and assert
   `sharedTimeNs - leader_now ≈ 1200ms` within generous tolerance
   (±400 ms). Then assert a second client's input shows 1200 (broadcast
   agreement) and a server restart preserves it (persistence).
6. Legacy show with `forward_sync` keys loads without error; the step
   inspector shows no forward-sync tick box; saving (touch any field)
   round-trips the file without the key (read the show JSON from disk).
7. No page errors.

## Acceptance checks (run these; all must pass)

```sh
~/.venvs/bopos/bin/python .loom/threads/15-show-polish/p3-global-transport-and-cue-lead.stitching/verify_show_transport.py
~/.venvs/bopos/bin/python .loom/tied/3-playback-engine/verify_show_engine.py
~/.venvs/bopos/bin/python .loom/tied/p1-zero-value-and-transport-bugs/verify_show_polish_bugs.py
~/.venvs/bopos/bin/python .loom/tied/p2-exclusive-playback-and-progress/verify_show_exclusive.py
~/.venvs/bopos/bin/python .loom/tied/4-tab-ui/verify_show_tab.py
~/.venvs/bopos/bin/python .loom/tied/5-inspector/verify_show_inspector.py
~/.venvs/bopos/bin/python .loom/tied/5b-compact-rows/verify_show_compact.py
~/.venvs/bopos/bin/python .loom/tied/5c-target-model-and-picker/verify_show_targets.py
~/.venvs/bopos/bin/python .loom/tied/6-message-editing/verify_show_editing.py
~/.venvs/bopos/bin/python .loom/tied/6b-show-management/verify_show_management.py
```

Tied suites that assert the forward-sync tick box, the sync hint, the
"Stop all" text, or fire_cue_now-for-shows may legitimately need minimal
amendments — amend and list each one in your report. Screenshot files
regenerated by tied suites are not yours to commit-restore them if changed.
Any other failure is a regression in your change: fix the change, not the
test. CSS edits go into the existing one-line show blocks in place — no
`!important`, no appended override blocks.

Do not commit. Write a report to
`.loom/threads/15-show-polish/p3-global-transport-and-cue-lead.stitching/codex-report.md`:
what changed per change-number, the exact state/broadcast plumbing you
found and copied for `cue_lead_ms`, tied amendments, verify output,
anything not done. If you could not complete the task, say so explicitly.
