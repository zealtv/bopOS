# Decisions

## Suppression belongs to the component, not to a surface

`css/value-box.css` now declares `appearance:textfield` plus the
`::-webkit-{inner,outer}-spin-button` reset on the unqualified
`input[type="number"]` selector the component already owns, so it reaches every
current and future consumer in both documents. The surface-scoped rule in
`control-panel.css` is deleted.

The old rule's own comment had the principle right — *"browser arrows in one of
them and not the others is exactly the incoherence this pass closes"* — but
applied it only within `:is(.live-card,.device-control,.show-inspector-section)`.
`05-value-box-component` extracted the face without carrying it, which is why
the drawer looked right and the manifest editor, Seats, event lead and Show
inspector fields did not. This is not a superseded ruling: nothing in
`05/decisions.md` or the ratified `design-language.md` mentions spinners at all.

## What stayed behind

`height:20px` and `color:var(--text)` remain on `.live-gen-num`. They are
genuinely drawer-local — a drawer arg is a shorter box than a parameter row, and
an `<input>` does not inherit the panel's colour the way an `<output>` does.
Only the two appearance declarations and the pseudo-element block moved.

## The scoping assumption held

The instructions said to grep rather than assume any drawer renders outside
those three containers. All three mount sites exist and cover every consumer:
`.live-card` (`facilitator.js:189`, and `control-surface.js` cards),
`.device-control` (`dashboard.js:1441`), `.show-inspector-section` (six
builders in `show.js`). So the drawer had no pre-existing gap of its own; the
divergence was entirely outside the drawer.

`value-box.css` loads last in both `index.html` and `facilitator.html`, and is
the only stylesheet in the app that styles `input[type="number"]`, so the
component rule wins without needing specificity tricks.

## Keyboard stepping survives

The named risk was that removing the buttons removes the behavior. It does not:
`appearance:textfield` changes the rendered face only. `ArrowUp`/`ArrowDown`
still step by the declared `step`, verified on an integer box. Event lead's
`step="50"` is read from the declaration as before.

## The spinner cannot be asserted through the DOM

`getComputedStyle(el, '::-webkit-inner-spin-button')` looks like the right probe
and is not: Chromium mirrors the host element's own values onto that pseudo —
it reported the input's `width` (153px in the probe) and the element's own
`webkitAppearance`, identically for a suppressed and an unsuppressed field.
Headless also never paints the spinner, so a Pillow pixel probe would pass
whether or not the fix were present — the vacuous-pass trap CLAUDE.md gotcha 11
already warns about, in a new place.

So the verifier asserts the *mechanism* (`webkitAppearance === "textfield"` on
static, dynamic and drawer fields) and pins the un-observable pseudo-element
half at source level: the component declares it, and no surface re-scopes it.
Both new assertions were mutation-tested — removing the two declarations from
`value-box.css` turns three checks red with `auto`.

Worth adding to gotcha 11 when the design language is extracted: **the absence
of a native shadow-DOM control is not observable headlessly by either DOM or
pixel means.** Assert the declaration.

## Pattern worth naming

Third instance of a rule living on a surface rather than on the component: the
`--chrome-*` split, the three widened Seats numeric rules `05` retired, now
spinner suppression. When `02-component-unification` extracts the design
language, it should say that a component face owns its own appearance
suppression and surfaces do not get to differ.
