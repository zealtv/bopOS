# 7-mute-all-honesty

**Status:** ready · small · Bob ruled 2026-10-03 ("yes")
**Goal:** "mute all" never reports output off while the device is still
making sound.

`set_mute` (`python/bopos.py`) sets `state.mute_all` before calling
`enforce_mute`, so a failed mixer call leaves the report claiming output is
off while sound continues. `2-device-enabled-honesty` fixed the same bug for
Device enabled (`cb2b535`): apply the mixer operation first, then change
live/persisted state, and send no success receipt on failure. Do the same
here, and keep the two paths consistent.

## Done when

- Test: mute fails → `mute_all` and the report are unchanged and no success
  is claimed; mute succeeds → behaviour as today.
- simfleet/audition model the same order if they model `mute_all` at all.
- Fast tier green. No new wording, wire field or engine-stop fallback (Bob
  ruled against stopping the engine, 2026-07-23).
- Hardware: same check as `2-device-enabled-honesty` — not claimed unless run.
