# Ratification — 2026-07-20

Bob pre-ratified this gate for the 2026-07-20 autopilot session ("including
pre-ratifying the ux gate automation-4 … get a few designers with different
profiles to have a look at it, and then get a ui/ux expert to synthesize").

Process: three independent designer agents (performance-instrument,
motion-dataviz, calm-ops-a11y — see `session.md` and the `expert-*.md`
files), then a UI/UX judge-synthesizer who verified the load-bearing claims
against the code (notably: `sh`/`drift` values are device-seeded PRNG draws
the dashboard can never reproduce; native range thumbs cannot be
CSS-animated; the value-axis/time-axis conflict on sliders). The orchestrator
reviewed the ruling and accepts it unchanged.

**The ratified design is `judgment.md`** — the three-layer treatment:
static mandatory kind-glyph in a new `--auto` token (Layer 1), paint-once
track state + CSS-progress fades (Layer 2), pure-CSS phase-anchored
value-axis marker for deterministic kinds only (Layer 3), with the single
real drawn curve reserved to the Show message inspector. No rAF in the
default path; `sh`/`drift` glyph-only; freeze-then-drain take-over.

One explicitly reversible default for Bob's later veto: **muted devices keep
the marker moving** (desaturated) because automation still runs downstream;
all three experts flagged stillness-on-mute as the calmer alternative. Flip
is a one-line CSS/state change.

Implementation split:
- `automation-3-animated-takeover` — generator tracking, take-over gesture,
  and the ruling's Slice 1 (static glyph layer = the "minimal placeholder").
- `automation-5-waveform-marker` (new stitch) — Slices 2 and 3.
