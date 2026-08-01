# 04-event-fire-affordance

Retire the Control-tab `#event-panel` and promote the control panel's `fire`
button to a first-class panel object with the lead-progress + fire-flash
feedback the retired `/cue` buttons had. Source: Bob's live 2026-07-28 review
of the shipped control panel; design ratified in-session (see `decisions.md`).

Bob's words: the events section at the top is wasted real estate (the event
buttons *and* the lead field go, whole section); the in-panel fire button
"doesn't feel clickable" and is missing the cue's progress bar + fire flash;
it should be a top-level UI object whose sizing, styling and alignment match
the other control-panel objects.

## Scope

1. **Delete `#event-panel`.** Section, its three-up event buttons, and the
   `#event-lead` field come out of `facilitator.html` / `facilitator.css` /
   `facilitator.js` — on the embedded Control tab *and* the standalone iPad
   view (Bob ratified dropping it on both; lead lives in the Monitor dock's
   Globals panel, desktop-only). Event *firing* survives via the panel rows.
   Keep the `event_scheduled` aria-live announcement.

2. **The fire button becomes a panel object.** 58 × `--row-h` on `--input`,
   1px `--control-line`, `--radius-momentary` (7px) — the same left column as
   every parameter's value box, so events and parameters share one alignment
   grid. The 7px radius is the panel language's existing momentary shape, not
   a one-off.

3. **Lead progress + fire flash.** Click sweeps a `--value-fill` wash across
   the button over the global lead, then flashes `--mod` cyan on fire
   (~260 ms). Lead `0` is sync-off: no sweep, flash immediately. Honour
   `prefers-reduced-motion` the way the retired `#declared-events` rules did.
   The surface needs the lead the host actually sent, so `sendEvent` returns
   it rather than the panel guessing.

4. **Events above parameters** in `paramTree`, and the same order in the Patch
   tab's manifest editor (Events subhead + list before Parameters).

Untouched: the event wire grammar (`/e/*`, contract v1.15), arity/labels,
manifest `kind`, and the ruling that every event forward-syncs.

## Verify

Extend the nearest living Playwright journey covering the control panel's
event row: the top `#event-panel` is gone, a fire click still puts the same
`fire_event` on the wire, the button carries its firing class for the lead
duration, and the Events section renders before Parameters on both hosts.
Then `tools/run-tests.sh fast`.
