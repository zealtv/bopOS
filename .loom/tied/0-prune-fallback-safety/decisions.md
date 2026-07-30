# Decisions — 0-prune-fallback-safety

Fixes the live target-widening defect ratified as D5 (`1-columns-design`,
Bob 2026-07-31). Scope was one behaviour on one host; everything below is
either the fix or something the fix uncovered.

## 1. `pruneFallback` is a `create()` option, not a spec field

The spec is rebuilt on every render from live venue state; whether a host may
be widened is a fixed property of the host. So it sits beside `storageKey` and
`followFocusSeat` in `create({...})`, defaulting to `"all"`. The Control
surface (`facilitator.js`) is the only host that passes `"empty"`; Assets keeps
today's advance-to-next-eligible behaviour, as the instructions required.

## 2. Only PRUNE goes empty — `toggle`/`remove` still fall back to All

Deselecting the last chip by hand still lands on All. That is an operator
action with immediate visible feedback in the same control they just clicked;
the defect is the *silent* substitution that happens while nobody is looking.
Widening the change to the click handlers would also make the empty state
reachable by ordinary clicking, which is not what it is for. Noted rather than
done, in case a later stitch wants it.

## 3. The picker names its casualties; the host writes the sentence

`prune` returning `[]` loses the information needed to say *what* went, so
`create` now keeps a `dropped` list and exposes `dropped()`. It survives
re-renders while the selection stays empty (the host is still displaying it)
and clears the moment anything is applied. The wording — `Seat 2 is no longer
in this venue.` — is the host's, because only the host knows a bare `"2"` is a
Seat and `"g0"` is a group. The component never learns what a selector means.

`reveal()` is on the component for the same reason in the other direction: the
host's `choose a target` button must not reach in and set `details.open`
itself.

## 4. Found while fixing: `markup` could not render an empty selection

`markup` coerced its selection through `list(spec.selection, ["all"])`, whose
documented behaviour is that an empty array takes the fallback. So the first
empty-target render painted **All pressed and a terse readout of `all`** over a
selection of nothing — the exact lie the fix exists to remove, one layer down.
An explicit empty array is now honoured; only an *absent* selection defaults.
Caught by the component check, not by inspection.

## 5. `presetScope()` had the same widening, one surface over

`!selection.length` reduced to `{scope: "all"}`, so capture-as-step would have
captured the venue from a target of nothing. It returns `null` now and the
capture button is not rendered at all while there is no target. Same reasoning
as D5's answer to the capture question: the safe reduction of "nothing" is
nothing, never everything.

## 6. Verification

- `tests/verify_target_picker.py` — the component: empty and *stays* empty
  across re-renders, `[]` is what persists, the casualty list, All still
  offered (and choosable) but never the fallback, and a third fixture picker
  that takes the default so `"empty"` stays opt-in.
- `tests/verify_control_tab.py` — the real journey: the picker is on Seat 2,
  Seat 2 is renumbered out from under it on the Seats tab, and the Control
  surface must render no cards and name the loss. Deliberately not a bare
  `wait_for`: a restored `["all"]` fallback fails as three named checks rather
  than as a 15 s timeout traceback.
- Both guards were confirmed to FAIL with `pruneFallback: "empty"` reverted,
  which is the property the instructions asked for.
- `tools/run-tests.sh fast` 255 OK; `browser` green.
