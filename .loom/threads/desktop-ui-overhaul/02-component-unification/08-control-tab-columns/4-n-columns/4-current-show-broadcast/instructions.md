# 4-current-show-broadcast

Make `current_show` reach the clients that read it, and fix the one surface
that is visibly wrong because it does not.

Found in passing by `2-venue-wide-capture`; queued here by Bob (2026-07-31) to
run after `3-chrome-demotions`. It is **not** column work — see "Where this
sits" below.

## The defect

`set_current_show()` (`dashboard/server.py`, ~1383) broadcasts `shows`, `show`
and `show_warnings`, but never a full `state`. And there is **no periodic
full-`state` broadcast anywhere in the server**: heartbeats go out as
`device_update`, and `offline_sweep()` only broadcasts `device_offline`.

So `installation.current_show` is not merely late after a show is created or
loaded — it is stale until some unrelated state mutation happens to trigger a
broadcast, which may be never.

**Measured, not inferred** (2026-07-31, two simfleet nodes at `--hb-interval
0.5`): a browser that created a show saw **zero** `state` messages in 20
seconds, and `installation.current_show` was still `null`.

The visible consequence is one line: `dashboard/static/js/monitor.js:699`
renders the Monitor System panel's `show` row from `installation.current_show`,
so with the show `opening` loaded the panel reads `none loaded`. A diagnostic
panel that lies about which show is loaded is the whole reason this is a stitch
and not a comment.

## The work

- Broadcast full state from `set_current_show`. Check **every** transition:
  `create_show`, `load_show`, the rename path, and the `delete_show` branch
  (~1311-1320) that clears `current_show` without going through
  `set_current_show` at all.
- Confirm the same class of omission is not sitting on a neighbour. The
  question to ask of each show verb is not "does it broadcast?" but "does it
  broadcast the plane it just mutated?" — `set_current_show` mutates
  `state.data`, and broadcasts three things that are not `state`.

## What NOT to do

`js/show-capture.js` deliberately gates on the `shows` catalog's `current`
rather than on `state.current_show` (`.loom/tied/2-venue-wide-capture/
decisions.md`). **Leave it.** It is not a workaround to be unwound once the
broadcast lands: `shows` is the more specific fact and the more direct
dependency, and a component that gates on the narrower signal is right whether
or not the wider one is timely.

## Verify

`tools/run-tests.sh fast` and `browser`.

The durable check is operator-facing, not structural — assert the panel says
the right thing, not that a particular broadcast fired, or the guard pins the
implementation instead of the behaviour (the failure mode
`23-waveform-marker-guard-regression` found three times). Create a show, then
require `[data-monitor-system="show"]` to name it.
`tests/verify_show_capture.py` is the closest template for the fixture
(real dashboard + simfleet + Playwright); `tests/verify_osc_transport_monitor.py`
already drives the Monitor dock and may be the better home for the assertion.

## Where this sits

Bob placed this after `3-chrome-demotions`, so it sorts fourth under
`4-n-columns` and `loom.sh next` serves it in that position. Worth being
explicit that it is an ordering choice, not a claim of kinship: nothing here
touches columns, and `4-n-columns` (and so `08-control-tab-columns`) now cannot
tie until an unrelated Monitor fix ships. If that ever becomes the thing
holding the thread open, lift this stitch up to
`desktop-ui-overhaul/02-component-unification` beside `09` and `11` — it loses
nothing by moving.
