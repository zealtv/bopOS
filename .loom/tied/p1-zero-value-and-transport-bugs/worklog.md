# p1-zero-value-and-transport-bugs — worklog

2026-07-19, autopilot session. Implementation delegated to GPT 5.5 (codex)
against `codex-spec.md`; results in `codex-report.md`.

- Zero-value fix: `renderParamBuilder` reads the raw stored arg with `??`
  (the `argValue` helper coalesces missing→`""` and can't distinguish
  stored-empty from absent). Full `||` audit table in the codex report —
  no other true instances in show.js / facilitator.js / dashboard.js.
- Transport: optimistic local `playback.steps` transition + immediate
  render in `sendTransport`; the server `show_playback` broadcast stays
  authoritative. Rapid play→stop verified honest.
- Next glyph redrawn as triangle+bar at 15×12; transport cell fixed at
  94px so the title never shifts.
- Orchestrator taste pass: codex delivered the CSS as a prepended
  `!important` override block; refolded into the original
  `.show-glyph-next` / `.show-step-transport` rules in place (house
  minified idiom, no overrides). Re-verified after the refactor.

Verification (run by the orchestrator, not just the delegate):
`verify_show_polish_bugs.py` 6/6 PASS post-refactor; tied 4-tab-ui and
5b-compact-rows re-run green. Codex additionally ran tied 5, 5c, 6, 6b
green pre-refactor (its report). No tied-verify amendments needed.
