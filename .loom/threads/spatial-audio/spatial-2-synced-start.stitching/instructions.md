# spatial-2-synced-start

Synced start of a named sample on all devices via `/cue` — the piece of Stage A
that needs `clock-sync` (sync-2 tied at minimum). Do this child last.

- [ ] Dashboard action: pick sample/param target, fire `/cue` at
      leader-now + lead-time to the fleet; devices fire in sync (clock-sync
      machinery does the work).
- [ ] What a cue *does* on the engine side is patch territory: the cue →
      engine message is the bare `/cue <cueId>` per contract; mapping cueId →
      sample playback inside the patch is Bob's PD domain. For agent
      verification, simfleet + helper.py fire-logs are the evidence; note the
      PD-side mapping as an item for Bob's pd-edits list.
- [ ] verify_*.py: cue a sim fleet, assert fire-time spread within loopback
      bound (reuse sync-3 harness).

When this ties and spatial-0/1 are tied, the parent's remaining condition is
the real-installation sweep — mark the goal `.waiting` on that (dashboard-goal
pattern), don't claim it done.
