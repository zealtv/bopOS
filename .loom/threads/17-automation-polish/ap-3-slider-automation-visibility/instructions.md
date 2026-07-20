# ap-3-slider-automation-visibility — make automated params visibly move

**Bob, 2026-07-20:** revisit the live-slider animation for automated
parameters. Three parts:

## 1. Fix the marker bug (do this first, it may explain everything)

The current CSS value-axis marker ("a blue dot sort of doing something")
misbehaves: on an LFO that should span 0→1 it moved unexpectedly rapidly
and appeared to cover only half the range, ~0→0.5, "like it wasn't zeroed
properly". Audit the marker math end-to-end
(`dashboard/static/js/paramspec.js` parse → marker CSS custom
properties/keyframes in `dashboard/static/css/style.css` and the JS that
sets them in `dashboard/static/js/dashboard.js`): amplitude/offset
normalisation against the param's min/max, phase anchoring, and the
period→animation-duration mapping. Reproduce with a known LFO (e.g.
`sin` 0→1 at 0.1 Hz) in simfleet and confirm the marker traverses the
full authored range at the authored rate before touching anything else.

## 2. Fades move the real slider

For deterministic *fades* ("for lines, I really do want to see those
sliders move"): the slider position itself should animate along the fade
(dashboard-side computation; wire discipline unchanged). Respect the tied
take-over behaviour (user touch freezes/drains per automation-3) and
`prefers-reduced-motion`. Periodic kinds (lfo etc.) keep the marker
treatment — the slider thumb stays put as ratified.

## 3. Clearer automation indication (single design pass)

The marker must be much clearer: "quite a lot larger", can sit behind the
slider's touch point — Bob suggests possibly a highlighted bar behind the
slider that moves to show the automated parameter. This revises the
ratified automation-4 treatment **at Bob's request**. Per Bob's
2026-07-20 ruling: run a **single Opus design pass** (not a full
council) — one agent, briefed with the automation-4 judgment
(`.loom/tied/automation-4-waveform-ux-gate/judgment.md`), Bob's feedback
verbatim, and screenshots of the current state; produce one recommended
treatment + implementation notes. Implement it, screenshot before/after
for Bob's veto, and record the change as an amendment note referencing
the automation-4 judgment (keep it in this stitch; point to it from the
tied judgment's thread if the house pattern allows a note file).

Constraints that still hold: `sh`/`drift` stay non-animated (device-seeded
PRNG; the dashboard cannot know their values); offline dimming; honest
`auto·mixed` aggregation; dashboard restart forgetting runtime automation
state is by design.

## Verify

Playwright + simfleet: (a) LFO 0→1 marker geometry — sample the marker's
animated position/box over time and assert it reaches near both extremes
of the track and its period matches the authored one within tolerance;
(b) a 10s fade visibly moves the slider input's value/thumb and stops at
the destination; (c) take-over still freezes; (d) reduced-motion disables
the movement. Remember CLAUDE.md Playwright gotcha 6 (animated nodes
never go "stable" — one-shot evaluate + fresh bounding_box).
