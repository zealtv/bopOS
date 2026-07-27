# Decisions — 8-kind-feedback-pass (2026-07-27)

All four are Bob's rulings from the live review of `6-non-float-kinds`. What
follows is how each was implemented and the judgment calls underneath.

## 1. "Can this control show the value?" is now one predicate

```
tracksValue = numeric row AND (fade OR marker-bearing LFO/loop)
pulse       = a generator is running AND NOT tracksValue
```

Everything else follows from it: which rows pulse, and which value boxes show
dots. Written as one expression rather than per-kind branches because the
rule Bob stated is about *knowability*, not about kinds — the same LFO that
tracks on a slider cannot track on a toggle, and a sample+hold cannot track
anywhere.

Chosen: **ring**, not fill. A pulsing fill would still read as a value
(a level rising and falling); a ring reads as a state of the control. It also
composes with the mixed hatch, which owns the fill.

## 2. The pulse anchor is the wall clock, not the generator

The pulse must survive the heartbeat re-render — a CSS animation on a
replaced node restarts, and at a 0.5–1 s heartbeat a 1.4 s pulse would never
reach its peak. The marker's negative-delay trick fixes that.

The choice was *what* to anchor to. Each generator's own `elapsedMs` was the
obvious parallel, but it makes every pulsing row breathe at a different
offset, which reads as noise on a panel with several generators running. The
pulse is not communicating phase — the marker does that where phase is
knowable — so a **shared wall-clock anchor** is both calmer and more honest.
The period travels from JS to CSS as `--pulse-period` so the two cannot
drift.

## 3. Toggle: PD toggle box + label beside it

The full-width bar read as a banner rather than a control (Bob). Options were
a fixed-width button with the name inside (the mockup's 96px) or a box with
the label beside it. Chose the box: it is PD's toggle, it puts the toggle and
the enum on one grammar (control in the left column, name beside it), and it
lines a toggle row's name up with a numeric row's name. `✕` marks the on
state — PD's own mark, and a non-colour channel for it.

## 4. The string kind stays — role clarified

`type: "s"` is in the ratified §2 kind table ("text box, no ∿") and shipped
long before this thread; it is not a new UI type. The confusion was the
fixture's param being *named* `label`. What was actually broken was the
height — the hosts style `.live-param input[type=text]` for their own chrome
(44 px on the tablet-first facilitator) and the panel never overrode it. It
is now one row tall with the name to its left.

**For Bob:** if no patch wants a text parameter on the control surface, say
so and it comes out — the row, the CSS and the manifest `"s"` type are all
still there because the ratified table says so, not because anything depends
on it.

## 5. Supersession recorded in the tied design

`design-language.md` §6 says a generator-driven toggle "flashes its live
on/off value". That is the line this stitch retires, so the tied document now
carries an inline note saying so and pointing here — the same discipline the
tied-guard rule asks for, applied to a design document, so the retired
behaviour cannot be re-implemented from the ratified source.

## 6. Test flake fixed in passing

`verify_live_param_kinds.py` drove its keyboard-commit checks with
`locator.focus()` then `page.keyboard.press()`. A heartbeat re-render between
the two calls detaches the focused node and the keystroke lands nowhere —
that was the file's one intermittent failure in the browser tier.
`locator.press()` re-checks actionability and does both in one auto-waiting
step. This is a *different* flake from the tied accordion-reload one already
flagged on `verify_control_surface_component.py`.
