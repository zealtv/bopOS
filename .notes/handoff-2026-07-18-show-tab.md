# Handoff — 2026-07-18 (second session): 14-show-tab complete

## State of play

Thread `14-show-tab` is **fully tied** — all eight stitches plus the two
post-review additions (5b, 5c). The reserved Sequencer tab is gone; the
**Show** tab is the primary performance-control surface: a show document
(steps/sections/messages) persisted per-show under `shows/` beside the
installation state, a playback engine with the complete then-action
vocabulary, compact Ableton-density rows with icon transport and
alias-hashed pill colours, a context-sensitive inspector with the
param/cue/point/raw message builder and a multi-target chip picker
(targets are selector *lists* since 5c — legacy string targets still
load), full structural editing (clipboard, arrange, keyboard), and two
always-on OSC consoles (osc_out/osc_in WS taps in `osc_bridge.py`) with
client-side `*`/`!` filtering. `dashboard/README.md`, `docs/GETTING-
STARTED.md`, and `CLAUDE.md` describe the finished slice; no stale
"Sequencer" references remain in the app or docs.

## Tied this session (commit hashes)

- `88e211f`/`d54d1ef` — 5b compact rows (row redesign, icon transport,
  pill palette)
- `448d770`/`fd1b32a` — 5c target lists + chip picker (schema amendment in
  the design note, engine fan-out, UI)
- `523687b`/`d534df6` — 6 structural editing (clipboard, arrange, divider
  focus, keyboard, stale-goto surfacing)
- `b55a319`/`b7d7337` — 7 OSC consoles (bridge taps + filtered panels)
- 8 docs-and-handoff — this commit

## Verify scripts (all green at tie time)

Every stitch's `verify_*.py` travels in `.loom/tied/<stitch>/`; run any
with `~/.venvs/bopos/bin/python <script>` from anywhere (repo located by
marker). The show-thread set: `2-model-and-persistence`,
`3-playback-engine`, `4-tab-ui`, `5-inspector`, `5b-compact-rows`,
`5c-target-model-and-picker`, `6-message-editing`, `7-osc-consoles`.
Cross-stitch amendments made this session (all logged in worklogs): tied 4
and 5 row-text assertions (5b's compact layout), tied 2's three
`target == "3"` equalities (5c's lists), tied 5's greyed-target check
(5c's picker).

## Simulator / wire compatibility

The wire is unchanged: a target list fans out as one datagram per selector
(`/3/p/gain`, `/g1/p/gain`, …) — identical frames to before, so simfleet
and audition configs needed nothing. The only simfleet change the thread
needed was stitch 3's cue-recv type logging, already tied there. The
target-list schema is dashboard-internal (show JSON + WS).

## Deferred by design (stays with Bob-gated scene-sequencing co-design)

Musical time / global transport, decomposed curves, point-motion
specification, the animated visualisation view (seats-like), and
multi-column Ableton-style layout. The 2026-07-18 braindump authorized
exactly the implemented slice; §8-scale decisions (scene language, curve
vocabulary) remain open co-design questions Bob owns.

## Next work

CLAUDE.md stage 10: resume `patch-workflow-friction/friction-0..1`.
**Gotcha:** those stitches don't exist in `.loom/threads/` — only
`friction-0a-readme-refresh` was ever tied. The next session must lay the
thread out first (check `.loom/tied/friction-0a-readme-refresh/` for the
original framing). The only current loose end besides that is
`notify-patch-lifecycle`; everything else is `.waiting` on Bob/hardware
gates.

## Usage at stop (session end, 2026-07-18 ~18:45 UTC+2)

- Claude 5-hour session: **~85%** (the binding cap; resets 12:00 UTC
  2026-07-18)
- Claude weekly (Fable): ~38%, weekly (all models): ~31% (reset 07-20
  09:00 UTC) — the next session has plenty of weekly room.
- Codex weekly: 76% used at session start; Bob's ≥20%-reserve rule meant
  no codex delegation this session (all stitches ran Claude-inline).
