# 16-param-automation

Parameter automation: one generator slot per numeric `/p/*` param — plain
values, single- and multi-segment timed fades, `loop`, `stop`, and LFOs —
sent as single messages and decomposed in bopos.py, with the Show-tab builder
GUI, animated dashboard controls with take-over, and the UX-gated waveform
visualisation.

Design: `.lore/items/2026-07-19-param-automation-generator-design/`
(braindump + draft proposal). Source authorization is Bob's 2026-07-19
braindump; direction agreed in-session, exact grammar **not yet ratified**.

Separate from `15-show-polish` (Bob, 2026-07-19). Implies a contract
revision (§3 shorthand registry; deferred §8 kind for strings/arrays —
name and plane open, see the ratification stitch). Do not implement past
the unratified design — decompose implementation stitches only after
`automation-0-design-ratification` ties.

**Ordering (2026-07-19):** this thread runs **after** `15-show-polish`
(bugs-first; and this thread's GUI stitches edit the same Show/live-control
panels p3–p7 touch — landing polish first avoids double churn and repeated
Playwright re-verification). One permitted interleave: once the design is
ratified, the dashboard-free stitches — contract amendment, bopos.py
generator engine, simfleet parity — may proceed in parallel with remaining
polish stitches. The docs close-out (ex-`patch-workflow-friction`, dropped
in-repo 2026-07-17; surviving pointer on the host loom at
`~/repos/.loom/threads/patch-workflow-friction/`) should land after this
thread, not before, or the docs go stale immediately.

Deferred by design (recorded in the proposal): musical time on the wire
(authoring layer + `scene-sequencing`), atom manifest kind for
strings/arrays, per-segment curves, square `duty:`, audio-rate modulation.
