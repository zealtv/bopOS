# 52-preset-drawer-name-discarded — decisions

## The cause: a guard that was never wired

`onfocusin` and `onfocusout` are **not event-handler IDL attributes**. Assigning
them creates an ordinary expando property that nothing ever calls — no error, no
warning, nothing observable in the DOM. Measured on a fresh element in Chromium:

```
'onfocusin'  in element → false
'onfocusout' in element → false
'onfocus'    in element → true
'onclick'    in element → true
```

and a handler assigned to `.onfocusin` fires **0** times where
`addEventListener("focusin", …)` fires once.

Both of the Control surface's editable drawers wired their heartbeat render
guard that way:

* `control-surface.js:487` — the preset save drawer;
* `control-surface.js:1071` — the generator drawer.

So the guard had **never once run**, in either drawer, since it was written.

The instructions asked for a timestamped trace rather than end-state reads, and
that is what settled it in a single run:

```
   t=176  renderCards  REBUILD  focus=BODY
   t=261  pointerup    False    focus=SUMMARY
   t=333  pointerup    False    focus=BUTTON
   t=334  renderCards  REBUILD  focus=BUTTON
   t=349  renderCards  REBUILD  focus=BODY
  t=1577  renderCards  REBUILD  focus=preset-name   ← the loss
```

`drawer.focusin` does not appear anywhere, and neither does `setInteracting`.
Not "the guard was released" — the guard was never armed. Both of the
hypotheses carried in the instructions were wrong, and both had looked plausible
precisely because a final-state read cannot distinguish "released" from "never
armed": `focusout` fires when the focused node is removed, so the aftermath of
the loss looks identical either way.

## What the operator lost

Type a preset name, pause about a second, and the field empties. `commit` then
reads `name === ""` and returns without sending, so the save silently does
nothing. The generator drawer had the same exposure for its argument fields.

It is also the cause of the browser suite's remaining red.
`verify_preset_control_surface.py` fails at its **first** assertion —
`wait_catalog` after `save_from_row` — because `fill` is wiped before `commit`.
That journey failed in full-suite runs 0, 4 and 5 while passing standalone,
which is what made it read as a flake through threads `47`, `50` and `51`.

## Two fixes, not one

**1. Arm the guard.** `addEventListener("focusin"/"focusout", …)` on both
drawers. `focusin` rather than `focus` because only `focusin` bubbles, and the
guard belongs on the drawer rather than on every field inside it. Listener
accumulation is not a risk: the drawer's markup is rebuilt every render, so
each `bindPresets` pass sees a fresh node.

**2. Write through the typed name.** `control-surface.js:356` emits the field as
`value="${esc(name)}"` from the `openSaveDrawers` entry, and nothing put what
was typed back into it, so the value only ever lived in the DOM. `oninput` now
stores it.

These are not alternatives and (2) is not belt-and-braces. The guard only
suppresses renders while focus is *inside* the drawer; a render provoked from
anywhere else after focus has left would still re-emit the field from a stored
`""` and empty it. The journey pins that case separately by deliberately
blurring, confirming the rebuild really happened, and then requiring the name to
have survived it.

(2) is guarded on `tagName === "INPUT"`: in `save`/overwrite mode the same
`[data-preset-name]` hook is a `<select>`, whose value is a chosen preset rather
than typed text.

## The guard against reintroduction

The defect is invisible: the code reads correctly, the comment above each site
sincerely claimed the guard was the same one a working surface used, and nothing
at runtime complains. Prose was already there and did not help — so
`tests/test_dom_event_handlers.py` bans assigning the non-IDL names outright.

It ignores comments, which is not fastidiousness: the fix documents the banned
names in prose directly above the corrected code, and the first version of the
guard flagged its own explanation.

Paired with a live assertion in the browser journey that these are still not IDL
attributes. If a browser ever makes them real, that check fails and the ban gets
revisited, rather than the rule quietly outliving its reason.

## Verification

See `verification.md`.
