# 07-control-surface-component — done

Extracted the live control surface from `facilitator.js` into
`dashboard/static/js/control-surface.js`. Pure extraction: no user-visible
change, which is what the stitch asked for.

## What moved

`window.ControlSurface.create(context)` returns
`{tree, control, bind, refreshAnchors, announcement, startFadeAnimator}` and now
owns: `valueForSeat`, `automationForSeat`, `aggregateValue`,
`automationPresentation`, `automationKey`, `refreshAutomationAnchors`,
`automationModel`, `scopeAttrs`, `paramControl`, `paramTree`, `fadeValueAt`,
`finishFade`, `animateFades`, `startFadeAnimator`, and the `[data-live-param]`
binding loop (takeover, throttled send, `PrecisionField.attach`, checkbox
indeterminate handling).

`facilitator.js` keeps what is genuinely its own: which cards exist
(`liveCard`, `renderCards`), the scope tabs, cues, master/silence, presets,
device commands, `deviceForSeat`, and `updateLocalParams`. It shrank from 608
to ~300 lines and now reads as a *page*, not a page plus a widget library.

Both `facilitator.html` and `index.html` load the new script — index.html needs
it for stitch 09.

## The seam, decided

The component holds no host state beyond the animation bookkeeping that must
survive re-renders (`automationAnchors`, `takeoverAnnouncements` — both moved in
wholesale). Everything else arrives through the context:

- `getState()` — the host's `installation`
- `deviceForSeat(seat)` / `deviceForScope(id)` — online + output gating
- `send({scope, id, name, value})` — **the host owns the wire.** The component
  never calls `ws.send`, and it no longer calls `updateLocalParams`; the
  facilitator's send callback does both, converting `id` to a Number for the
  seat/group scopes it uses.
- `setInteracting(bool)` / `requestRender()` — the render guard the precision
  field needs, which the component cannot own because it is a host `let`.

`scope: "device"` is accepted by the renderer now (it takes the seat-scoped
single-member branch and the seat-style online/output gating), but **no host
renders it yet** — that is stitch 09, which also has to solve where a pinned
device's declarations come from. Adding it here rather than in 09 is what makes
the "same component, different send" property testable today.

## Verification

- `tests/verify_control_surface_component.py` — **new, 11/11 green.** Owned by
  the code surface, not the stitch (thread-27 policy). Pins: the component
  loads on both pages; all/group/seat all render through it; nested branches,
  strings and 0/1 booleans keep their kinds; a `device`-scoped render is
  **markup-identical** to a `seat`-scoped one once scope/id attributes are
  normalized; and a device-scoped row calls the *host's* send with the device
  scope and uid.
- `tests/verify_live_param_checkbox.py` — 10/10 green (regression net).
- `tests/verify_precision_param_input.py` — 13/13 green.
- `automation-5-waveform-marker`'s guard, run from a copy per the CLAUDE.md
  rule — **19/19 green**, which is the real proof the automation rendering
  (markers, phase anchoring, fade animation, takeover, reduced motion) survived
  the move intact. Copy deleted afterwards.

## Flake seen once, not caused here

`verify_live_param_checkbox.py`'s "slider change-commit reaches the wire"
failed on one of four runs (three consecutive green after). The test focuses the
slider and presses ArrowRight, but `focus()` does not set the `interacting`
render guard — only `pointerdown` does — so a heartbeat re-render landing
between focus and keypress destroys the element the keypress was aimed at. That
race is in the test, and predates this stitch. Left alone rather than fixed
opportunistically; noted here so the next reader doesn't chase it as a
regression.

## Noted, not done

`dashboard.js` has a second, simpler renderer for the patch editor
(`editorControl` / `editorParamTree`, ~line 696). It authors *manifest
declarations*, not live values, so unifying it is a different problem — recorded
as a later candidate host, deliberately out of this bite.
