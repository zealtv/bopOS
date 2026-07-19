# 16-param-automation

Parameter automation: one generator slot per numeric `/p/*` param — plain
values, single- and multi-segment timed fades, `loop`, `stop`, and LFOs —
sent as single messages and decomposed in bopos.py, with the Show-tab builder
GUI, animated dashboard controls with take-over, and the UX-gated waveform
visualisation.

Design: `.lore/items/2026-07-19-param-automation-design-ratified/` is the
ratification authority; the earlier braindump/draft remains at
`.lore/items/2026-07-19-param-automation-generator-design/`. The exact grammar
is ratified and recorded in OSC contract v1.8 §3.2.

Separate from `15-show-polish` (Bob, 2026-07-19), which is now fully tied.
`automation-0-design-ratification` and `automation-1-engine-and-parity` are
tied: contract §3.2, the bopos.py generator engine, and simfleet parity are
landed. The next stitch is `automation-2-show-builder-gui`. The deferred §8
kind for strings/arrays still has no name or plane and is not part of this
thread's remaining GUI work.

**Remaining ordering (2026-07-19):**
`automation-2-show-builder-gui` → `automation-3-animated-takeover` →
`automation-4-waveform-ux-gate`. The last stitch must stop for Bob's UX
ratification before waveform implementation. The docs close-out
(ex-`patch-workflow-friction`, dropped in-repo 2026-07-17; surviving pointer on the host loom at
`~/repos/.loom/threads/patch-workflow-friction/`) should land after this
thread, not before, or the docs go stale immediately.

Deferred by design (recorded in the proposal): musical time on the wire
(authoring layer + `scene-sequencing`), atom manifest kind for
strings/arrays, per-segment curves, square `duty:`, audio-rate modulation.
