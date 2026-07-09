# sync-3-jitter-harness

The honest measurement tool: something that records how tight cues actually
fire across N devices, reusable on sim (now) and hardware (sync-4).

- [x] `tools/sync_measure.py`: a minimal clock leader (sync + offset push, same
      low-RTT-median math as `osc_bridge.py`) that fires a cue burst and collects
      per-device fire timestamps. Fire evidence = the `fire_mono=<ns>` log line
      (added to `sync_node.py`'s CueScheduler here; simfleet already had it).
      Computes cross-device spread (max/typical) + per-device offsets, writes a
      Markdown report.
- [x] Hardware mode (`--mode hardware`): syncs real LAN nodes, prints per-device
      offsets and the expected fire schedule (leader clock) to align an external
      GPIO/click recording. Designed + smoke-run (no fleet); the real run is
      sync-4.
- [x] Ran against simfleet; baseline committed as `sync-baseline-report.md`
      (5 devices, ±40 ms skew → max spread ~1 ms, the software floor). NB: multi
      real-helper.py on one host is blocked by helper's hardcoded ports
      (7770/6660) — flagged below; simfleet is the multi-device sim vehicle,
      and sync-2 already proved one real helper.py fires on loopback.
- [x] Usage documented: this stitch + a `dashboard/README.md` "Clock sync & cue
      timing" section (the hardware one-liner for Bob).
- [x] `verify_sync_measure.py`: exercises both modes; asserts every cue measured,
      spread within the floor ceiling, non-trivial offsets (cancellation), and a
      clean hardware-mode run.

Loopback numbers are a floor — the report says so up top.

**Flag for the next session:** running several *real* helper.py instances on one
host isn't possible (fixed ports 7770/6660); parameterising helper's ports would
let a richer all-software audible/real mix run — a possible small follow-up
stitch, not required for clock-sync.
