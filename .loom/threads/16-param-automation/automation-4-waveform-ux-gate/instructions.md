# automation-4-waveform-ux-gate

The waveform visualisation on automated controls — doubling as the
automation indicator, fading out on touch (the animation dying under your
finger is the feedback that the control is now static).

**This is a Bob decision gate.** Bob wants a UX-designer eye on an app-wide
treatment before any implementation (ratification record,
`2026-07-19-param-automation-design-ratified`). The work here is:

1. A written UX proposal: where the waveform lives in each control type
   (slider, toggle, numeric), size/contrast/motion at Ableton density, the
   fade-out interaction, mixed-aggregate and offline states, and how it
   coexists with the mute/solo and mixed-value affordances. Mockups or
   annotated screenshots over prose where possible.
2. Mark this stitch `.waiting` and surface the proposal to Bob.
3. Implement only after ratification, then the usual Playwright verify.

Do not implement past the unratified waveform UX proposal. `automation-3` ships with at
most a minimal placeholder indication.
