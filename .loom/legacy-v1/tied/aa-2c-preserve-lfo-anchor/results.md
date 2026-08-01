# Preserve synchronized LFO anchor — results

## Finding

The first phase repair supplied an authoritative leader-monotonic sample, but
`refreshAutomationAnchors` still treated every new `sent_at` as a new visual
animation instance. Bob confirmed that the saved `go` step's 10-second loop
visibly restarted its 4-second LFO marker at each cue retrigger, while audio
continued on the synchronized absolute-time phase.

An identical non-free LFO application is idempotent in the shared node
generator. The facilitator now applies the same rule: when the argument list is
unchanged and the LFO is not `free`, it preserves the existing visual anchor.
Changed arguments and free LFO applications still create new instances.

## Verification

- `verify_lfo_anchor_browser.py`: 3/3. It launches the real Dashboard,
  simfleet, and facilitator in Chromium; runs a 2.5-second looping step with a
  1-second triangle LFO (the same half-cycle retrigger relationship as the
  saved 10-second/4-second `go` cue); confirms the OSC resend and bounds the
  marker's cross-retrigger displacement; and reports no browser errors.
- Prior phase-sample regression `aa-2b/verify_lfo_retrigger_phase.py`: 4/4.
- `node --check dashboard/static/js/facilitator.js` passed.
- The adjacent slider automation browser suite passed its first seven marker,
  period, geometry, and retired-element checks, then its tracked screenshot
  step hit the suite's known heartbeat-rerender detach (`Element is not attached
  to the DOM`). The focused real-browser regression above exercises the changed
  retrigger behavior directly and passed.

No Pure Data file or saved Show file was changed. Human A/V confirmation of the
saved `go` cue remains the parent stitch's final gate.
