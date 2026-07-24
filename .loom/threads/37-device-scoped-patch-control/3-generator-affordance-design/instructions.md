# 3-generator-affordance-design (thread 37)

Per-parameter generator editing (choose an LFO, set rate/depth, etc.) directly
on the shared control surface — not only via the Show inspector's message
builder. The `automation-2` generator-builder GUI already compiles to the OSC
§3.2 wire grammar; **extract/reuse it**, don't duplicate.

## Activated + reparented (Bob, 2026-07-25)

Un-waited from `feature-backlog/38-generator-editing-on-surface` and brought into
thread 37. Bob wants it addressed **ahead of** the preset primitive
(`41-preset-primitive`) — a preset that can capture "values *or* generator specs"
needs the per-param generator affordance to exist on the surface first.

## This is a Bob-gated design (user-facing Dashboard IA)

Output is a **written HTML proposal with mockups**, ratified by Bob before any
implementation. Proposal artifact + source live in this stitch
(`proposal-generator-affordance.html`). Ends `.waiting` for Bob after the
proposal lands; do not implement past the unratified design.

## What the proposal must settle

- Where the generator control lives on each host of the shared surface (live
  All/Group/Seat control card, per-device Device-tab panel, patch editor).
- The affordance to switch a numeric param between a static value and a
  generator (LFO/…); reusing the `automation-2` builder GUI + waveform UX from
  the tied `16-param-automation` thread.
- How a generator's presence reads on a control that also has a typed value
  (thread 40 precision entry) and a pinned/patch context (this thread).
- Runtime take-over / static-treatment consistency with the tied automation
  runtime (Slice-1) so the surface and the Show inspector agree.
- What a generator means *inside a preset* stays `41`'s design — name the seam,
  don't design presets here.
