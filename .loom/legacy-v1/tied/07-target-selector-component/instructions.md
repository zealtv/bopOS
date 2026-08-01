# 07-target-selector-component

One target picker, two domains.

Two unrelated implementations exist:

- `js/seat-filter.js` (`SeatFilter`, 117 lines) — All / Groups / Seat radio
  tabs plus a seat `<select>`. **Single**, mode-exclusive selection. Documented
  as "deliberately not a widget belonging to the Control tab" but has exactly
  one real consumer (`facilitator.js:90`); `dashboard.js:1136` only uses its
  `selectSeat` storage helper.
- `js/show.js:287` `renderTargetPicker()` — a `<details>` disclosure over a
  chip grid: All + group chips + seat chips, **multi-select and mixable**, with
  a removable summary row and a terse closed-state summary.

Bob, 2026-07-30, wants the Show picker's model everywhere: *"all or a selection
of groups or a selection of seats or a mixture of all of them using that
consistent target UI device."* So the unified component is closer to the Show
picker; `SeatFilter`'s exclusive model is what gets retired.

**Two domains, one chrome.** Bob: *"here we're targeting devices rather than
seats. So perhaps a device picker and a seat picker are two different things."*
Correct, and the tied entity architecture review backs it — seats/groups are
the site layer, physical devices are the hardware layer. Design one component
parameterised by domain: same disclosure, chips and summary; different roster
source and different wire selector. Device consumers today are `#patch-target`
(`index.html:83`) and `#asset-target` (`index.html:130`).

Consumers to integrate before tying: the Show inspector, the Devices tab, and
whatever `SeatFilter` currently serves. `08` and `09` then consume it.

Keep the shared-selection behaviour that exists for a reason: the selected seat
is one `localStorage` key so choosing a Seat on the Seats tab and opening
Control lands on the same Seat. Decide explicitly whether multi-select targets
are shared the same way or are per-host.

Verify: CLAUDE.md gotcha 12 — `data-uid` is not unique across rosters; scope
roster clicks to their container. Gotcha 13 — a Seats-roster row's centre is
its name `<input>` and the row handler ignores clicks inside inputs.
