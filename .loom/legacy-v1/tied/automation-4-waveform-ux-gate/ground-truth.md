# Ground truth — waveform visualisation UX (automation-4)

Verified by the orchestrator, 2026-07-20. Experts: read the cited files
yourself; treat anything not cited here as "verify, don't assume".

## What the product is

bopOS: a Raspberry Pi + Pure Data framework for networked multi-device sound
installations. The **dashboard** (`dashboard/static/`) is a dark-theme
browser operator tool used by a facilitator/operator, often on a touch
tablet, sometimes in daylight. Design tokens live at the top of
`dashboard/static/css/style.css` (`--bg:#101316 --panel:#191e23
--line:#303942 --text:#e8edf1 --dim:#8f9ba5 --green:#45d483 --amber:#f2b84b
--red:#ff4e5d`; system-ui 15px; Ableton-like density in the Show tab).

## What is being designed

Parameter automation is ratified (OSC contract `docs/OSC-CONTRACT.md` §3.2):
each numeric `/p/*` param has ONE generator slot — constant, timed fade(s),
loop, LFO (sine/tri/saw/square/sh/drift), or stop. Last message wins.
Touching an automated control sends a plain value and thereby KILLS the
automation (take-over). The dashboard knows which generator it sent and
shares the fleet's synced clock, so it can animate automated controls
locally with zero extra OSC traffic (that mechanism is `automation-3`,
being built separately with at most a minimal placeholder indicator).

**This design gate**: the app-wide *waveform visualisation* treatment —
the "this control is automated" rendering that doubles as the automation
indicator, and whose dying-under-your-finger fade-out is the take-over
feedback. Bob's ratification record
(`.lore/items/2026-07-19-param-automation-design-ratified/`) requires a
UX-designer eye on an app-wide treatment before implementation. Stitch
instructions: `.loom/threads/16-param-automation/automation-4-waveform-ux-gate/instructions.md`
(this dir's sibling; the `.stitching` dir you are reading is the claimed one).

## Where automated controls appear (the surfaces to cover)

1. **Facilitator live view** `dashboard/static/js/facilitator.js` —
   `paramControl()` (~line 68) renders each promoted param as a
   `label.live-param` with: text input (string decls — never automated),
   checkbox (int 0..1), or `<output>` + `<input type=range>` slider.
   Cards for All Seats / each Group / each Seat (`liveCard()`), nested
   param branches (`paramTree()`).
2. **Dashboard live tabs** (All & Groups / Seats) — same control vocabulary.
3. **Seat detail / patch editor sliders** `dashboard/static/js/dashboard.js`
   ~line 659.
4. **Show tab** `dashboard/static/js/show.js` — messages that *send*
   generators; the builder GUI is `automation-2` (in flight). A waveform
   preview inside the Show message inspector is in scope if the design
   wants it.

## Hard constraints (verified)

- **Mixed aggregates**: All/Group rows aggregate member Seats; when values
  differ they render a "mixed" state (placeholder "mixed", indeterminate
  checkbox — `facilitator.js` `aggregateValue`/`paramControl`). An
  All/Group row over *different per-Seat generators* must show an honest
  "automated" indication without pretending to a single value.
- **Offline/unbound**: durable stored values survive offline devices; an
  automated param's stored full-state value is the catch-up constant, not a
  stale animation frame. Offline controls must not animate as if live.
- **Zero added OSC traffic** for animation; all rendering is local
  simulation. CSS-driven progress is the house precedent (commit `7162943`
  replaced full-DOM countdown re-renders with CSS progress) — per-frame
  full-DOM re-render is culturally rejected; per-frame canvas/rAF on a few
  small widgets is acceptable if cheap on tablets.
- Controls coexist with: mute (device mute exists; Seat/Group mute/solo
  deferred), the mixed-value affordance, disabled/empty states, `dashboard:
  true` promotion, nested param branches.
- Dark theme only today (`color-scheme: dark only`); a light/dark toggle is
  anticipated soon — do not hard-bake contrast that only works on black.
- Density: Show tab is compact Ableton-style rows; live cards are roomier
  but still dense (15px base font, ~10px paddings).
- Touch-first: drags/taps on sliders are the take-over gesture; the
  animation must not steal pointer events or make the slider harder to grab.

## What the proposal must cover (from the stitch instructions)

Where the waveform lives in each control type (slider, toggle/checkbox,
numeric/output, aggregate rows); size/contrast/motion at this density; the
take-over fade-out interaction; mixed-aggregate and offline states;
coexistence with mute/solo and mixed-value affordances. Mockups (HTML/SVG/
ASCII annotated) beat prose.
