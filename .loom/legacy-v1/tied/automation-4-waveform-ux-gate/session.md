# Council session — waveform visualisation UX (automation-4)

Convened 2026-07-20 by the autopilot orchestrator (Fable 5). Bob pre-ratified
this gate for this session: the synthesized design becomes the ratified
design, recorded here in place of a `.waiting` pause.

## Roster

| Seat | Lens | Mandate | Model |
|---|---|---|---|
| performance-instrument | Pro-audio / instrument interaction designer (Ableton, TouchOSC, hardware surfaces lineage) | Make automation feel like a musical instrument state, legible mid-performance; motion vocabulary and take-over feel | Opus (agent) |
| motion-dataviz | Data-visualisation & motion designer | Honest, cheap, legible waveform rendering at tiny sizes on dark UI; what to draw per generator kind, and what NOT to draw | Opus (agent) |
| calm-ops-a11y | Accessibility & operational-calm reality check | Distraction budget, vestibular/motion safety, daylight/tablet legibility, offline/mixed honesty, perf on cheap hardware; find the constraint that kills elegant designs | Opus (agent) |
| judge-synthesizer | UI/UX expert synthesizer | Verify load-bearing claims against the code, name the crux, rule on one app-wide treatment | Opus (agent), reviewed + ratified by orchestrator under Bob's pre-ratification |

Experts run independently, in parallel, each writing
`expert-<lens>.md` into this dir.

## Spread

Real divergence, no contrarian seat needed:

- **performance-instrument**: the control itself is the playhead — motorised-fader
  metaphor, phase-anchored CSS on the existing slider, 12px shape+period
  legend, 180ms drain-under-finger take-over. No separate drawn lane.
- **motion-dataviz**: one reusable **automation lane** — static SVG of the
  generator drawn once + a single clock-seeded GPU-composited CSS playhead;
  deterministic futures drawn, sh/drift futures dashed-unknown; silent on
  constants; freeze-then-fade take-over.
- **calm-ops-a11y**: static mandatory kind glyph as the indicator; the only
  motion is the already-computed value marker at ≤20 fps shared clock,
  visible controls only; reuse the ratified CSS-progress mechanism; the one
  real drawn waveform lives only in the single-focus Show inspector.
  Kill-constraint claims: per-control animated waveforms blow the Pi-class
  tablet frame budget, and a slider's value axis conflicts with a waveform's
  time axis.
