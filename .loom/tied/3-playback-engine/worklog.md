# Worklog — 3-playback-engine (2026-07-18)

Implemented by a Sonnet delegate against design note §3/§4; diff reviewed
and both verifies re-run by the orchestrator (Fable).

Delivered: `dashboard/show_engine.py` (393 lines — per-step state machine,
duration timers, play-n-times, then-action resolution with any/other
shuffle-bag, goto_missing flag, non-wrapping walks, synchronous-chain
guard, forward-sync via fire_cue vs fire_cue_now); transport WS messages +
`show_playback` snapshots in server.py; both stitch-3 TODO hooks filled;
simfleet gained a `cue-recv ... shared_time_ns_type=` log line so verifies
can assert the wire-string law.

Verification (orchestrator-run, both green):
- `~/.venvs/bopos/bin/python .loom/threads/14-show-tab/3-playback-engine.stitching/verify_show_engine.py` → "All checks passed." (32 checks: message-set atomicity, play-n-times, chains, any/other section semantics with exhaustion, multi-then, pause/resume freeze, stop_all, scheduled vs immediate cue paths with string sharedTimeNs, remove-while-playing, no tracebacks)
- `.loom/tied/2-model-and-persistence/verify_show_model.py` → 0 failures (delegate fixed a latent proper-subset loop bug there that the new connect-burst message exposed).

Notable engine bug caught by the verify: eager shuffle-bag discard during
two-phase stop→start transitions wiped the bag every hop; fixed by reaping
stale bags once per settled trigger.

Deviations accepted: /pt and unknown addresses send via raw bridge.send
(args stored wire-order); no run-context seed reaches the dashboard
process today — engine reads BOPOS_SEED env if present, real seed plumbing
flagged as a gap (candidate future stitch, not blocking).
