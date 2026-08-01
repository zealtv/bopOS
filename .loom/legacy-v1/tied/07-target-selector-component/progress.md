# 07-target-selector-component — progress

Shipped 2026-07-30. One target picker, two domains; both prior implementations
retired.

## What shipped

**The component.** `dashboard/static/js/target-picker.js` (`window.TargetPicker`)
and `dashboard/static/css/target-picker.css` — the app's **third** component
stylesheet, loaded by both documents after `value-box.css`, like
`param-generator.css`.

Surface:

| member | for |
|---|---|
| `markup(spec)` | the disclosure, chips, summary and terse closed state |
| `action(event)` | what a click inside a picker means (`toggle` / `remove` / null) |
| `create({host, …})` | imperative hosts: owns selection, persistence, open state, one delegated listener |
| `list` `toggle` `remove` `terse` `labelFor` `chipOn` | the selection algebra |
| `seatSections` `deviceSections` | the two rosters — the only domain knowledge in the file |
| `focusSeat` `focusedSeat` `FOCUS_SEAT_KEY` | the one shared cross-tab Seat |

Declarative hosts that re-render whole templates (the Show inspector) use
`markup` + `action`; hosts that own an element (Control, Assets) use `create`.

**Consumers, all integrated before tie:**

1. **Show inspector** (`js/show.js`) — `renderTargetPicker` is now eight lines
   calling `markup` with `seatSections`, and `targetList`/`terseTargets`/
   `toggledTargets` delegate to the component's algebra. Group chips keep the
   portable `group:<name>` selector with `g<id>` as the alias, because a Show is
   portable.
2. **Control surface** (`js/facilitator.js`) — `SeatFilter` is gone. A target is
   now All, or any mixture of groups and Seats, and **each selected entry gets a
   card**. Group chips carry `g<id>` here: nothing is persisted into a portable
   document and an id cannot be ambiguous.
3. **Assets tab** (`js/dashboard.js`, `index.html`) — the device `<select>` is
   replaced by the single-select device domain. Every discovered device is a
   chip; an ineligible one is present but disabled, wearing its reason.

**Deleted:** `js/seat-filter.js` (117 lines), its five `.target-filter*` rules in
`facilitator.css`, its two `localStorage` keys' mode half, the 20 `.show-target-*`
rules in `style.css`, `#asset-target` and its three `.asset-target-select` rules.

`#patch-target` is deliberately untouched — `09-patches-deploy-row` owns it, and
the component is ready for it (`allowAll` with a "Whole fleet" label, single
select over devices).

## Verification

- `tools/run-tests.sh fast` — **255 pass**, including the ownership guard with
  `target-picker` registered.
- `tools/run-tests.sh browser` — **all 20 journeys pass**, including
  `verify_live_param_kinds.py` (the known flake) on this run.
- **New:** `tests/verify_target_picker.py` — the component's own contract in two
  passes. (a) 28 checks on a fabricated origin: both domains' chrome, the
  selection algebra, All's exclusivity, single-select replacement, per-host
  persistence, the shared focus seat, re-render focus/scroll survival, pruning a
  departed selector, and the two appearance rulings (near-square latching chip,
  purple selection chrome). (b) the device domain against the real dashboard on
  the **Assets tab, which had no living journey at all** before this file.
- Updated in place: `verify_control_tab.py` (mode tabs → chips, plus new checks
  that a mixture yields a card per entry and All is exclusive),
  `verify_event_control_panel.py`, `verify_control_surface_component.py`,
  `verify_show_reference_foundation.py` (class renames, scoped — see gotcha
  below).
- 24 app screenshots in this stitch (every tab × 1280/1680 × light/dark, plus the
  standalone Remote panel and card), from `shoot.py` — copied from
  `02-token-promotion` with its `bopos.theme`/`bopos-theme` bug fixed and a
  Show-tab step that selects a message so the inspector's picker is on screen.
- `touch_probe.py` — the tap-target measurement `49-remote-ipad-restyle` asks
  each collapse to make. Result recorded in that stitch.

## Two things a later stitch should know

**A component class is app-wide, so a bare component selector is now ambiguous.**
`verify_show_reference_foundation.py` broke on `.target-picker` resolving to two
elements — the Show inspector's and the Assets tab's, the latter in an inactive
tab and therefore never visible. This is CLAUDE.md Playwright gotcha 12
(`data-uid` is not unique) in its component-class form, and it will recur for
every component this thread extracts. Scope to the host (`#show-root
.target-picker`).

**`about:blank` denies `localStorage`.** A `set_content` fixture page cannot test
persistence at all — the component's own try/catch makes it look like it works.
`page.route` + `goto` on a fabricated https origin gives a real origin with no
server and no app scripts, which is how pass (a) runs.
