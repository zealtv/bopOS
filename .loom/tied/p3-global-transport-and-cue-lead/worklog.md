# p3-global-transport-and-cue-lead — worklog

2026-07-19, autopilot session. Implementation delegated to GPT 5.5 (codex)
against `codex-spec.md`; results in `codex-report.md`.

- Global transport: play/pause-resume, stop, next as compact glyph
  buttons in the strip's actions cluster, all routed through
  `sendTransport` so p1's optimistic rendering covers them. Play targets
  the active step, else the focused step (a focused message resolves to
  its containing step), else the first step. Stop-all keeps danger
  semantics as a glyph-only button with aria-label/title. The playing
  indicator simplifies to the exclusive model ("1 playing/paused: name").
- Forward-sync retired: every Show `/cue` goes through
  `bridge.fire_cue`; the per-step flag, tick box, mixed hint, and its
  CSS are gone; `clean_step` accepts-and-drops legacy keys;
  `.notes/show-tab-design-2026-07-18.md` carries a dated amendment.
- Global `cue_lead_ms` (default 500, clamp 100..10000) persisted in
  installation state on the exact `master` pattern; `set_cue_lead` WS
  verb; the engine reads the live value through a callable at fire time.
  Placement decision: the lead input sits with the transport buttons
  (transport policy lives with transport controls, not the diagnostic
  consoles). Facilitator's per-fire `#cue-lead` now defaults from the
  broadcast value until locally edited.
- Codex trimmed transport-strip vertical padding 18→10 px to keep the
  new controls inside the 5b dense-layout budget — visual change
  reviewed and accepted (fits the compact idiom; the tied 768×1024
  check is the arbiter).
- Tied amendments (logged in the codex report): 3-playback-engine
  (forward_sync fields gone; both Show cues scheduled), 5-inspector
  (asserts the retired controls are absent).

Verification (orchestrator-run): `verify_show_transport.py` 14/14 PASS —
including the wire-level check that a Show cue's sharedTimeNs lands
≈ the configured lead ahead of leader-now, two-client agreement, and
restart persistence; tied 5b, p2, 6b, 5-inspector re-run green. Codex
ran the full ten-suite acceptance green (its report).
