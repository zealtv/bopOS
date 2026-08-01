# p2-exclusive-playback-and-progress — worklog

2026-07-19, autopilot session. Implementation delegated to GPT 5.5 (codex)
against `codex-spec.md`; results in `codex-report.md`.

- Exclusivity is one hook in `ShowEngine._begin` (stop every other active
  uid before installing the new one) — covers manual starts and all
  then-action paths; paused steps count as active. No schema change; the
  `show_playback` steps map is unchanged.
- `snapshot()` additively exposes `"armed": <uid|null>` — non-null only
  with exactly one active step and one deterministic then-action
  (next/previous step or section, valid goto, play_again). Random kinds
  and multi-action steps never pre-resolve. Recomputed per snapshot.
- Client renders a `.show-step-progress` fill layer (width from the
  countdown interpolation the 500 ms tick already does; green playing,
  amber paused, frozen while paused) and a `.show-step-armed` 1.8 s
  border pulse. No layout movement.
- Tied `3-playback-engine` verify amended (logged in the codex report):
  additive `armed` key in the connect payload, exclusive expectation in
  the stop-all precondition, and the old bind-port-0 allocator replaced
  with the house random-port pattern.

**Extra product bug found during acceptance** (surfaced by p1's optimistic
render changing verify timing, but real and operator-facing): the 500 ms
countdown re-render rebuilt the saved-shows picker with the current show
selected, wiping an operator's uncommitted dropdown choice while any step
played. `render()` now carries an uncommitted pick — a live select value
differing from the option rendered `selected` — across the rebuild.
Without this, choosing a show from the dropdown during playback was
near-impossible (the tied 6b suite caught it as a deterministic timeout).

Verification (orchestrator-run): `verify_show_exclusive.py` 9/9 PASS;
tied 6b twice 0 failures after the picker fix; tied 3-playback-engine,
p1 suite, and 4-tab-ui green. Codex additionally ran tied 5, 5b, 5c, 6
green (its report). One transient p1-verify TypeError under parallel
suite load did not reproduce standalone (bounding-box read race in the
test, not product).
