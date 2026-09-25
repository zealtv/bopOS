# Handoff — Assets 11a complete (2026-07-16)

This supersedes `.notes/handoff-2026-07-16-seat-groups-complete.md` as the
current launch note.

## Current state

- Seat-group workspace delivery is committed as `f797073`.
- Device asset inventory (`11a`) is tied. Loom has 124 tied stitches, 13
  dropped stitches, no active claim, and Assets 11b is the next accepted step.
- OSC contract v1.6 now exposes durable observed device asset slots. Nodes use
  a persistent stat-signature hash cache, seed it at fetch completion, warm it
  outside the OSC loop, and never hash content in the reply path.
- Simfleet mirrors query/fetch/refetch/drop behavior. The dashboard distinguishes
  unknown from observed empty, records observation time, quarantines individual
  malformed entries, and retries unresolved fingerprints with capped backoff.
- The focused verifier passes 27/27; adjacent group state passes 6/6 and Seat
  state/server regression passes. Exact retained stale-verifier caveats are in
  `.loom/tied/11a-device-asset-inventory/results.md` after tie.
- Assets 11a production changes are uncommitted. No `.pd` file changed.

## Next implementation session

1. Read `CLAUDE.md`, this handoff, and run `./.loom/loom.sh status`.
2. Claim/resume `11b-single-device-assets-workspace`.
3. Build the accepted one-online-device Assets workflow on the durable 11a
   observation. Do not grow it into fleet rollout; that remains the separate
   `asset-fleet-distribution` goal.

## Verification caveats

- `bop000`, the installation LAN, physical iPad, SD-card cold-read timing,
  audio engine, and audible rig were not exercised.
- Older retained verifier failures are stale assertions, not 11a regressions;
  see the tied 11a results for the exact boundaries.
