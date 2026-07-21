# decisions — 02-retire-listener-toolbar

## The transient on-canvas readout: implemented, small

The stitch asked me to decide explicitly whether a drag-only readout replaces
the retired `#listener-readout`, and to recommend rather than over-build.

**Decided: yes, one small gesture-only label.** Bob's ruling was that all
*control* can be graphical — he did not say the values must become invisible,
and range in particular is not judgeable by eye to any precision. A single
`<text class="listener-value">` sits just below the collar (clear of the heading
handle at any aim), is `opacity: 0` by default, and fades in only while a
gesture is live. It reports the value being changed:

| gesture | shows |
|---|---|
| range (collar scrub, wheel, arrow up/down) | `5.73 m`, `(max)` at the ceiling |
| heading (tip drag, shift+arrows) | `142°` |
| position (puck drag) | `3.4, 5.6 m` |

That is the whole feature — one element, one CSS class, no chrome. Anything
larger (a persistent HUD, a docked inspector) would be a proposal, not a fix.

## aria-label is now the only durable textual statement

With the numeric fields gone, the puck's `aria-label` is the sole place the
values exist as text. It was previously written once at render, which was
adequate only because the toolbar carried the live values. It now updates from
`describeListener()` on every gesture, and carries position as well as heading
and range.

## The label's fade uses a deadline, not a timer reset

First implementation restarted a 900 ms timer on every `describeListener()`
call. That never expired: the keyboard and wheel paths send `set_listener`, the
server broadcasts, `render()` rebuilds the puck, and the replay call reset the
timer — so the label stayed up permanently, at roughly heartbeat rate.

Fixed by splitting real gestures from *replays*: `paintRange(..., replay)` and
`describeListener(..., replay)`. Only a real gesture sets the
`valueLabelUntil` deadline and arms the timer; a re-render merely restores a
label that is still within its window. The guard pins this — the check "the
value label fades after a keyboard nudge (no end event)" fails against the
timer-reset version.

Pointer gestures need no timer: `pointerup` calls `render()`, which rebuilds the
puck. The deadline just makes them behave consistently with the keyboard paths.

## Superseded tied guard: `.loom/tied/02-listener-range-implementation/`

Repaired in place, per CLAUDE.md "Re-running a tied guard" (this is the second
repair — `/01` made the first; both are noted inline and in the module
docstring). 32/32 green after:

1. **`readout reports the max`** drove `#listener-readout`, which no longer
   exists. Retargeted to the puck's `aria-label`, which is now where that text
   lives. (Formatting gotcha: JS `round()` renders 5.0 as `5`, so the assertion
   formats with `f"{d:.2f}".rstrip("0").rstrip(".")` rather than Python's
   `round()`.)
2. **The whole "Numeric field" block** typed into `#listener-range` /
   `#listener-heading`. Its *subject* — range commits, range clamps at the
   diagonal ceiling, heading and range stay independent — is still valid, so it
   was retargeted to the **wheel**, one of the graphical range paths that
   replaced the fields. It is now a "Wheel over the puck" block.
   Gotcha found doing it: the wheel steps a fixed 0.25 m **per event**, not per
   `deltaY` unit, so one `wheel(0, -8000)` is a single notch. Reaching the
   ceiling needs a loop of events.
3. **`typed heading commits without touching range`** was dropped rather than
   retargeted: the property it asserted is already covered twice over by
   `dragging the tip does NOT change range` and `turning by keyboard leaves
   range alone`. Retargeting it would have been a third copy.
4. **The keyboard block's `210` / `225` literals** arrived from the retired
   typed-heading step. Rather than rewrite the literals, heading 210 is now
   arranged through a `set_heading()` **fixture-setup helper** that goes
   straight through `set_listener`. Setup is not an assertion about a control,
   so routing it through the state channel is honest; the graphical paths are
   what the checks themselves drive.

## Not done

No replacement for the toolbar's implicit "the listener exists and simulation is
live" affordance was added — the puck itself already carries that, and it only
renders when simulation is active.
