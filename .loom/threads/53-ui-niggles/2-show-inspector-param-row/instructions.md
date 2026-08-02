# 2-show-inspector-param-row

> in the inspector in the show tab. when i click generator, the value box
> remains (fine), but if i set the phase of an lfo, for example, the value box
> disappears. there is the affordance of clicking the value button - but that
> is confusing and the disappearance is unexpected. instead - the parameter
> should display a parameter slider (the same component as in the control
> panel), with the same behaviour as the control panel. visible automation
> where possible. clicking and dragging the slider or number box sets to static
> value. if automation is messy from a ui/ux perspective, simply have the
> generator icon remain blue is enough to indicate the generator is active.
> choose whichever approach is cleanest. — Bob, 2026-08-02

Bob named the acceptable fallback himself, so this is **not** a design gate.
Ship the cleanest of the two and record which, and why, in `decisions.md`.

## Measured starting state

`dashboard/static/js/show.js:745` `renderParamBuilder`. The value field is
conditional on the parsed mode:

```js
const mode = parsed?.mode || "value";
const fields = rawFallback ? renderParamRawFallback(message)
  : mode === "value" ? renderParamGeneratorFields(declaration, parsed)
  : mode === "stop"
    ? '<p class="dim show-param-stop">Automation is stopped…</p>'
    : "";
```

So for `fade`/`loop`/`lfo` **`fields` is the empty string** — the value entry
is not hidden, it is not rendered. What replaces it is the `Value` / `Stop`
button pair in `drawerActions` (`:770`), which is the "affordance of clicking
the value button" Bob calls confusing. The disappearance is one line.

Note the sequence Bob describes: choosing a generator leaves the value box up
(because nothing has been committed yet and `parsed.mode` is still `value`),
and it vanishes on the first field edit that compiles a real generator message.
That is why it reads as a glitch rather than a mode change.

## What "the same component as in the control panel" means here

`window.ControlSurface` (`js/control-surface.js`) is already mounted by four
hosts — the Control column, the Device panel, the Remote view and the Patch
editor (`06-control-panel-reflow-and-editor`). This would be the fifth, and it
is the one that is **structurally different from the other four**, which is the
whole substance of this stitch:

* The four live hosts drive a **running value on a Seat**. Their automation
  marker is animated from `state().automation[<seat>][<identity>]` —
  runtime state, refreshed by anchors (`refreshAutomationAnchors`), with a real
  `startFadeAnimator`.
* The Show inspector authors a **message**. There is no seat, no runtime, and
  nothing is playing. The "automation" is the message's own args.

So "visible automation where possible" has no live signal to visualise. Two
honest readings, and the stitch must pick one:

**(a) Authoring-time row.** Mount the row's *appearance* and takeover
behaviour, with the generator's own parameters (period, phase, shape) driving a
static or self-animating preview from the message args rather than from
`state().automation`. Closest to Bob's first description. The cost is a second
model feeding a component whose every existing consumer feeds it the first one
— check `automationModel` / `automationPresentation` (`:91`, `:140`) before
committing, and prefer passing a model in over teaching the component a second
source.

**(b) Bob's stated fallback.** Row always renders — slider plus value box, both
always present and always editable. A live generator turns the `∿` cyan and
leaves it cyan; no marker, no animation. Drag or type and the message becomes a
static value.

`automation-5-waveform-marker` already built a **Show-inspector preview** — read
that tied stitch before choosing, because if the preview it shipped is the
marker Bob means, (a) may be much smaller than it looks.

Whichever is chosen: cyan is the right colour and it already means this.
`04-event-fire-affordance` widened `decisions.md`'s `cyan = modulation` to
"something is driving this, continuously or discretely".

## Scope

- The value entry never disappears for any mode, including `stop`.
- Drag/type on the slider or number box sets a static value — the same takeover
  the control panel does (`control-surface.js:906`, `takingOver`/`takeoverSent`).
- The `Value` button in `drawerActions` goes; it exists only to undo the
  disappearance. Decide `Stop`'s fate explicitly rather than by omission —
  `stop` is a distinct wire message (§3.2), not the absence of a generator, so
  it probably stays.
- The `mode === "stop"` prose ("Automation is stopped. Set a value or choose a
  generator.") is replaced by the row, not kept beside it.
- **Out of scope:** the `text` kind, which has no slider and belongs to
  `44-event-plane/6-text-kind-control`; and `renderParamRawFallback`, which is
  the escape hatch for args that do not parse and must keep working.

## Verify

Extend `tests/verify_show_*` — the nearest living journey that drives the Show
inspector's message builder.

Three traps from CLAUDE.md that bite this exact surface:

* **gotcha 10** — changing the inspector's generator `<select>` writes new args
  through onto the focused message. Use one fixture message per generator kind
  rather than switching kinds in-test.
* **gotcha 23** — a `<input type="range">` cannot test whether focus holds the
  render guard, because the pointer pair releases it a tick after the gesture.
  If you assert the guard, focus a numeric box.
* **gotcha 6** — CSS-animated automation markers keep nodes perpetually
  unstable, so `scroll_into_view_if_needed` never settles. One-shot
  `page.evaluate` `scrollIntoView` plus a fresh `bounding_box()`.

The regression to pin is the report itself: **set an LFO phase, and the value
entry is still there.** Fail it against the current tree first.
