# 3-preset-dropdown-menu

> The asterix isn't visible on a preset name when it has been modified if the
> name is too long. put the asterix at the start. move new, save, and delete
> into the dropdown, at the top, with icons, separated from presets by a
> divider. lose the edit button. — Bob, 2026-08-02

Four rulings, all ratified. The first is a one-line move. The other three are
a change to a **shared component**, so read the whole stitch before sizing it.

## Measured starting state

`dashboard/static/js/control-surface.js:373` `presetRow`.

```js
const marks = `${entry.slug === appliedSlug && provenance.dirty ? " *" : ""}${entry.drift ? " ⚠" : ""}`;
return `<option …>${esc(entry.name)}${marks}</option>`;
```

The marks are **appended**, and the row's control is a native `<select>`
(`:427`). A closed `<select>` ellipsises its selected option's text at the end
when the name is longer than the control, so the dirty `*` and the drift `⚠`
are the first two things to be truncated — precisely the state they exist to
announce. Move both to the front, not just the `*`; they have the same defect
for the same reason, and splitting them leaves the second half of the bug.

`new` / `save` / `del` are `PRESET_ACTIONS` buttons (`:406`) inside a
`<details class="live-preset-authoring">` whose summary is the word `edit`
(`:418`). That disclosure is not a legacy accident — it is D8, shipped days ago
by `4-n-columns/3-chrome-demotions`, deliberately **on the shared surface** so
Control, Device and the patch editor all got the demotion together. Bob is now
asking for the next step in the same direction: not a demotion but a merge.
Say that in `decisions.md` rather than letting a later reader think D8 was
reverted.

## The constraint that decides the shape of this stitch

**A native `<select>` cannot be the target of these rulings.** Three separate
reasons, any one of which is sufficient:

* Its options render plain text — no icons.
* A separator is at best `<hr>`/`<optgroup>`, which is not the divider being
  described and is not consistently stylable.
* Fatally: a `<select>` models a **value**, and `change` fires for every
  option. Putting `new`/`save`/`del` in it makes three commands
  indistinguishable from three preset choices — `bindPresets` (`:441`) would
  have to demultiplex verbs out of a value change, and the closed control would
  briefly display an action's label as if it were the applied preset.

So this becomes a **disclosure-based menu**, the idiom the app already has:
`TargetPicker` (`js/target-picker.js` + `css/target-picker.css`) is a
`<details>` whose summary carries a terse readout of the current value, and
`.live-card-overflow` (`control-column.js:258`) is a `<details>` menu of
actions with `icon-menu` opting out of design-language §9's `▸`/`▾`. This is
both of those at once. Expect the app's **seventh component stylesheet**, and
expect `test_css_component_ownership.py` to hold you to it.

`09-patches-deploy-row` is the counter-case worth reading first: it measured
`TargetPicker` at **51px closed against a 37px row** and declined to mount it.
Measure the closed height of whatever you build against the row it replaces
before committing to the pattern.

## Every mount point changes at once

`presetRow` is called from `control-column.js:301` (Control tab column, Remote
does not call it at all — `full` is false there per `41` Q4) and from the
Device panel and Patch editor via the same `ControlSurface`. There is no
per-host fork to hide behind: whatever this becomes, all three get it.

Behaviour that must survive the rewrite, all of it currently load-bearing:

* the empty option is an **explicit recall-none** that clears provenance
  (`:441-446`) — not a placeholder;
* `provenance.mixed` renders a disabled `·····` placeholder and a distinct
  aria-label; a mixed card must still be legible and must not silently apply;
* `savable` vs `appliedSlug` gate `save` and `del` differently on purpose
  (`:401-409`) — `save` needs a preset to *exist*, `del` needs one *showing*;
* `saveDisabled` (F8): capture from a target you cannot hear is illegal, so
  `new`/`save`/`del` stay gated on it while apply does not;
* unreadable entries render `disabled` and must not become clickable;
* the drift `⚠` and the `schema changed` chip (`:399`) are different signals;
* `del` is patch-scoped for the whole installation and the menu says so
  (`:422`). Keep that sentence somewhere.

## Two shipped bugs this surface has already had — do not re-earn them

* **`52-preset-drawer-name-discarded`.** The save drawer's render guard used
  `drawer.onfocusin = fn`, which is an inert expando because `onfocusin` is not
  an event-handler IDL attribute. Typed preset names were silently discarded
  for as long as the guard existed. Use
  `addEventListener("focusin"/"focusout", …)`;
  `tests/test_dom_event_handlers.py` bans the non-IDL names in source and
  `tests/verify_interaction_guard.py` asserts live that they are still not IDL
  attributes.
* **`50`'s gotcha 22.** `verify_preset_control_surface.py`'s `open_authoring`
  waited on `document.querySelector('.live-preset-authoring')?.ontoggle`
  page-wide while clicking a host-scoped element. If the `edit` disclosure goes
  away, that helper must be rewritten rather than re-pointed — and the
  replacement's wait and click must name the **same** host-scoped element.

## Verify

`tests/verify_preset_control_surface.py` is the living journey and will need
real work, not a selector swap. Add:

* a preset whose name is long enough to truncate in a 342px column, applied and
  then dirtied — the `*` is still visible. Fail this first; it is the report.
* the three actions reachable from the menu on all three `full` hosts, with the
  gates above intact.
* `del`'s confirm and `new`/`save`'s drawer still reachable and still
  committing a typed name after a heartbeat re-render (that is `52`'s
  regression, and this stitch moves the code it lived in).
