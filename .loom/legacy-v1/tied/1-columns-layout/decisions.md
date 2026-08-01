# Decisions — 4-n-columns/1-columns-layout

The Control tab holds N columns. Authority is `.loom/tied/1-columns-design/`
(`decisions.md`, then `proposal.md`); this file records what the implementation
ruled where the instructions left a choice, and the four findings that only
appeared once it was built.

## Shipped

- **The track is 342px, fixed, left-aligned**, in `style.css` on
  `#control-column-host > .control-column` as `flex: 0 0 342px` — positioning
  only, so the tab places the component without restyling it and
  `test_css_component_ownership.py` stays green. `#tab-control{max-width:none}`
  drops the 1400px cap on this tab alone.
- **The row is one viewport-height flex row that scrolls sideways**, and each
  column scrolls its own body. Its height subtracts the Monitor dock's
  `--monitor-reserved-height`: the dock is `position:fixed`, so a row sized to
  the viewport runs its last rows underneath it.
- **`bopos.control.columns`** holds `{id, target, open}` per column, in order,
  with minted ids. `bopos.target.control` migrates into column 1 once.
- **`+ column`** in a new strip, **`✕`** in each column head, minimum one — at
  N=1 the ✕ is `visibility:hidden`, which also takes it out of the tab order.
- **Open in Control** in the Seats inspector: focus a column already showing
  that Seat, else append one, then switch tabs.
- **One live region per column**, prefixed with the column's target. The
  per-card `.live-param-status` is deleted, and `ControlSurface` gained an
  optional `announce` context hook so a multi-card host can own its own region.
- **The grip reorders**, and the reorder writes the same ordered layout record
  rather than a second model of it. It was going to be decorative — no ratified
  decision asks for reordering — but a grip with `cursor:grab` that does
  nothing is a worse answer than either shipping it or dropping it. Dragging is
  armed by the grip alone: a permanently `draggable` column would make every
  fader inside it a drag handle, and a fader that starts a drag instead of
  moving is a control that stopped working.
- **D6's informative `mixed`**: the preset row's placeholder reads `dusk +2`.

## Four things the build decided

### 1. The strip's right-hand slot is not a placeholder — capture moved into it

The instructions asked for an empty slot that `2-venue-wide-capture` would
fill. That is only viable if the per-column `Capture as Show step` button
stays, and at N columns it becomes N buttons sending N different scopes —
which is exactly what D1 rules out, and three of the five column shapes capture
something other than what they show. Deleting it instead would have left
capture unreachable on this tab (the Show edit bar's `✛ Capture` is `2`'s work,
not something that exists yet).

So capture left the column and became one venue-wide `scope:"all"` action in
the strip. That needs no server change — today's `_capture_show_seats` under
`scope:"all"` already means every seat — and it leaves `2` its actual scope:
removing `scope` from the wire, the armed non-modal preview, and the derived
step name. `presetScope()` and `handleShowCapturePreview` left the column with
it; the dialogs live in `control-host.js` until `2` replaces them.

### 2. A restored column must not render before the first `state`

Rendering at mount prunes every stored target against an empty venue, and D5
then correctly reports every column as "no longer in this venue". The shipped
N=1 host never rendered at mount — it only looked safe by accident. Restored
columns now render on the first `state` message; a hand-added column renders at
mount, because by then the venue is known.

### 3. `<details>` fires `toggle` for a re-render that changed nothing

`TargetPicker` replaces its markup on every heartbeat. Reinserting a
disclosure in the same state still fires `toggle`, so the picker was writing
its open state back on every heartbeat — which is why a column stored as
closed came back open, and why a `page.evaluate` that seeded a closed layout
was overwritten before the reload it was seeding. The listener now compares
against its own state before acting; `reveal()` does the same.

### 4. A dead selector is KEPT, not rewritten

The instructions say an inert column keeps "its slot and dead selector", so a
prune does **not** write through to the layout record: `onTargetChange` fires
for operator actions only. A column whose Seat comes back therefore recovers,
and `verify_control_tab.py`'s D5 assertion moved from
`bopos.target.control == []` to "the layout record was not widened to All".

## Superseded assertions (CLAUDE.md's narrow rule)

- `tests/verify_preset_control_surface.py` pinned the dotted `·····` mixed
  placeholder. D6 ruled that mixed carries its content, so it now pins
  `Dusk +1`. Commented in place, naming `1-columns-design` D6.
- `tests/verify_event_control_panel.py` clicked target chips directly. The
  Control picker is closed by default (D4) and chips inside a closed
  `<details>` resolve but never become visible, so the journey opens it once.

## One honest note about test flakiness

Opening the picker shifted this journey's timing relative to the 0.5s
heartbeat and started landing on a pre-existing race — the same family as the
open `47-live-param-kinds-flake` — where a node resolved by one render is
measured after the next. A detached node reports a zero rect **and an empty
computed style**, so the failure read "the fire button has no width" rather
than "you measured a corpse". Two measurements became one retried
`wait_for_function`, and `click_once` re-measures rather than raising. Clean
`main` passed 4/4 before the change and this file passes 8/8 after; the race it
was landing on is older than this stitch.

## Evidence

`shoot.py` here drives the real tab with the same fixture, seats, groups and
seeded provenance as `1-columns-design/mockup.py`, so `control-*.png` here
are directly comparable with the ratified `mockup-*.png`: three columns at
1280, four at 1680 (the fourth a mixture rendering a card per entry), five at
2560 (the fifth an emptied group, disabled and `aria-disabled`), and
horizontal scrolling with no reflow at 760.
