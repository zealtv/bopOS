# 3-chrome-demotions — decisions

D8 shipped as ratified. All three demotions landed; nothing about what any of
the controls *does* changed.

## The one question the stitch owed: component or Control-only?

**The component.** The preset disclosure is in `ControlSurface.presetRow`, so
Control, the Device panel and the patch editor all get it. A per-host fork is
the pattern this thread exists to delete, and the instruction said to prefer
the component unless there was a reason not to. There was none: `new`/`save`/
`del` are authoring on every one of those surfaces, and the `<select>` is the
live act on every one of them too.

The card's ⋯ overflow is different and is **Control-and-Remote only**, because
it is `ControlColumn`'s markup rather than the surface's — the Device panel and
the editor have no card head to put it in and no `Send all` to demote.

## What moved

| control | before | after |
| --- | --- | --- |
| `Send all` | button in every All/Seat card head | inside the card's ⋯ overflow, both hosts |
| `new`/`save`/`del` | three buttons in the preset row | inside the row's `edit` disclosure, all three surfaces |
| `Device setup` (Update bopOS / Reboot / Shutdown) | `<details>` at the foot of every Seat card | **Remote only**; Control offers `Device setup…` in the ⋯, which hands off to the Devices tab |
| preset `<select>` | in the row | unchanged — applying is the live act |

The hand-off follows `07`'s `Set patch…`: `openDevice` selects the device and
switches tabs. Remote is passed no `openDevice`, which is why it keeps the
commands themselves — it has no Devices tab to hand off to, and an iPad away
from the rack is where a per-device reboot earns its place.

`del` is patch-scoped while everything else in its row is target-scoped. D8
asked for that to be made legible while it moved: the disclosure carries one
line of prose saying so. The button still does exactly what it did.

## The arithmetic, measured rather than asserted

`shoot.py` boots the real dashboard + simfleet, restores the three columns D8
costs (`all`, a group, and a mixture of a group plus two seats — five cards),
and counts the chrome controls **an operator can reach without opening
anything**. Screenshots beside it, 1280px, both themes.

|  | before | after |
| --- | --- | --- |
| All card | 5 | 3 |
| group card | 4 | 2 |
| Seat card | 6 | 3 |
| **three columns, five cards** | **25** | **13** |

The proposal's "six per card / fifty-four" was costed against a Seat card with
every affordance present; the measured Seat card is 6 before and 3 after, so the
per-card claim holds exactly and the totals differ only because this rig's three
columns render five cards rather than nine.

The counter's first version reported *no* change, and that is worth keeping:
**`offsetParent` is not null inside a closed `<details>`**. Chromium suppresses
disclosure contents with `content-visibility`, not `display:none`, so every
demoted button still reported an offset parent. The count asks the structural
question (`closest('details:not([open]) > :not(summary)')`) instead. The same
trap would make a naive Playwright "is it hidden?" assertion pass vacuously.

## A defect this stitch found and fixed

`shoot.py` could not reproduce its own three columns twice running: the second
and third came back reading *"Group 0 is no longer in this venue."*

**Cause.** `1-columns-layout` knew a restored column must not render before the
first `state` — it would prune every stored target against an empty venue and
D5 would then correctly report them lost — and kept `mount` from rendering. What
it missed is `ws.on("device_update")`, which renders every column and **can beat
the initial `state` to the socket**. Worse, the prune *persists*
(`target-picker.js` `resolve` → `persist`), so this was not a flicker: it
**erased the operator's stored layout permanently**, and every later load was
unresolved too.

Fixed in `js/control-host.js`: one `venueKnown` flag, set by the `state`
handler, gating the three render-only handlers. `addColumn` still renders
directly, which is correct — a column added by hand is added long after the
venue is known.

No browser guard: the trigger is a socket race whose losing side is exactly what
a test would have to arrange, so a guard would be either flaky or a
reimplementation of the bug. `shoot.py` retries and reports each lost attempt,
which is how it was caught; the retry loop is left in for that reason.

## Tests

`verify_control_tab.py` gained the demotion assertions (no `.device-commands` on
a Control card, `Send all` present but not visible until the ⋯ is opened, the
hand-off selecting the device and switching tabs) and, at the end, the Remote
half — `/facilitator` still draws the command disclosure and offers no hand-off.
That needed `facilitator_commands` in the fixture, which had always been empty.

`verify_preset_control_surface.py` and `verify_preset_editor.py` each gained an
`open_authoring` helper. Assertions that only *read* a demoted button were left
alone: a hidden element still reports `disabled`, so those checks are unchanged
and still mean what they meant.

`fast` 260 and all 21 browser journeys pass, including `verify_live_param_kinds`
(the known `47` flake) on this run.

## For `feature-backlog/49-remote-ipad-restyle`

Remote's `Send all` moved into the ⋯ overflow along with Control's — the
demotion is the component's shape, not a desktop-only one. The commands
themselves are untouched there. Whether a touch operator wants `Send all` one
tap deeper is a question for the deliberate iPad pass, on real hardware.
