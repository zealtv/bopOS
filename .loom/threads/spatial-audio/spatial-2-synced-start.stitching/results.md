# spatial-2 results

Added a deliberately small synced-cue panel to the technical spatial dashboard:

- validated named cue/sample ID;
- 100–10000 ms lead time, default 500 ms;
- one `/cue <cueId> <sharedTimeNs>` fleet broadcast using leader monotonic time;
- button locks through the fire window to prevent accidental duplicate fires;
- confirmation status is shared to connected dashboard browsers;
- no scene sequencing or facilitator control was introduced.

## Verification

`verify_synced_start.py` — **8/8 pass** with the real dashboard leader,
headless Chromium, and five simulated nodes with ±40 ms clock skew and 2 ms
jitter:

- UI sends and confirms the named 700 ms cue;
- duplicate-fire lock and unlock;
- all five devices fire;
- cross-device loopback spread ≤20 ms;
- distinct device-clock deadlines prove offset conversion;
- fire occurs ahead rather than immediately;
- cue remains a bare named event, never a patch parameter.

JS/Python syntax checks and `git diff --check` pass.

## Boundary

What `sample-start` does is patch-owned. The SC starter already has the cue
receiver; the PD `/cue` receiver remains item B3 in
`.notes/pd-edits-for-bob.md`. Audible meaning and real WiFi spread require the
rig. The simulated spread is only the software floor.
