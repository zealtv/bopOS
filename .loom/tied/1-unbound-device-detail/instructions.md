# 1-unbound-device-detail

Fix the Devices-tab detail crash for a newly discovered, unbound physical
device when `installation.live_controls.declarations` is non-empty.

## Current failure

`dashboard/static/js/dashboard.js:1199-1211` deliberately passes an empty
member list for an unbound Device:

```js
deviceSurface.tree("device", d.uid, seat ? [seat] : [], declarations, disabled)
```

The shared surface treats `device` like `seat` and calls
`valueForSeat(members[0], ...)`; `dashboard/static/js/control-surface.js:33`
then reads `seat.params` from `undefined`. The click itself succeeds and the
row gets `selected`, but the exception leaves the old “Select a physical
device” placeholder in the detail panel.

## Root cause and prescribed fix

The `"seat"`/`"device"` branch in `paramControl`
(`control-surface.js:204-206`) is a hand-inlined special case of
`aggregateValue()` for a one-member list — and unlike `aggregateValue()`, it
carries an unstated invariant that `members[0]` exists, which the Device tab's
own unbound call site violates by design. For a single member the two paths
are equivalent: `aggregateValue([seat], decl)` yields the same value, `mixed`
is trivially false, and the single automation entry passes through unchanged.
For an empty list `aggregateValue` already does the right thing: declaration
default, no mixed state, no automation.

**Fix by deletion, not by guard:** remove the `"seat"`/`"device"` special case
and route every scope through `aggregateValue()`. The empty-members render
then structurally cannot crash, and an unbound device shows declaration
defaults on disabled controls — exactly the ratified rule (unbound controls
visible but disabled; no content control sent without a Seat binding).

Two things to check while making the change, not new behavior to add:

- `sourceSeat = members[0]` remains `undefined` downstream for the empty case;
  confirm `automationModel(...)` and `automationKey(...)` tolerate it (both
  look null-safe — `automationForSeat` guards `!seat`, `automationKey` uses
  `seat?.id ?? "none"` — but verify, don't assume).
- Display source for the unbound case is **declaration defaults** via
  `aggregateValue`'s empty branch. Do not invent a Seat, do not synthesize a
  view model from the device's observed `params`, and do not weaken
  server-side target validation. If defaults later prove wrong as a display
  source, that is a separate ruling for Bob, not scope creep here.

## Required behavior

- Selecting an unbound physical device renders its full Device detail:
  identity, health, assignment, patch diagnostics, actions, Device enabled,
  audio/log/report placeholders, assets hand-off, and Device control.
- Device control remains visible and disabled with the existing explanation
  that live content targets require a Seat binding; controls show declaration
  defaults.
- Bound, offline, pinned-patch, Control-tab, and facilitator shared-surface
  behavior must remain unchanged — the one-member parity argument above is the
  reason this fix is safe; the tests below make it checked, not argued.

## Flow-on effects to be aware of

- **This fix opens a door stitch 2 makes usable.** With the crash gone, the
  full unbound Device-detail surface — assignment, Device enabled, audio
  config, log destination, patch pinning / Set patch hand-off, asset hand-off,
  admin actions — becomes reachable on a fresh device for the first time in
  practice. Those features are UID-scoped and designed for the unbound case,
  but on this Mac their sends can still fail silently until
  `2-macos-osc-routing-shutdown` lands. Do not claim admin round-trips in this
  stitch's verification; assert rendering and non-emission only, and leave
  round-trips to stitch 2's hardware adoption check.
- **Defaults on display can be misread as device readings.** Disabled unbound
  controls now show declaration defaults next to real device diagnostics. The
  existing "bind this device to a Seat first" copy carries the disabled-ness;
  check whether it also makes the *values'* provenance clear (e.g. "showing
  patch defaults") and adjust the one line of copy if not — no larger UI work.
- **The unification touches every surface consumer** — Control tab
  (All/Groups/Seats scopes), facilitator, and Device tab all flow through
  `aggregateValue()` afterwards. Aggregate scopes already used it, so the only
  behavior change is the formerly special-cased single-member path; the parity
  assertion below is what keeps this a refactor rather than a behavior change.
- **Downstream simplification, no action needed:** the waiting preset
  primitive thread (`41`) builds on this surface; a single value path is a
  simpler base for it. Nothing to do here beyond not reintroducing a
  per-scope value branch.

## Verification

Add or extend a living Playwright test under `tests/` using a fresh physical
record shaped like the Imani record in `../diagnosis.md`:

- unbound, online, `report`/`patches`/`assets`/`declared` initially null;
- fleet live-control declarations present;
- click the Device roster row;
- assert selected styling, Imani detail/assignment/actions, disabled control
  rows showing declaration defaults, and zero `pageerror`;
- assert no live parameter/automation message is emitted while unbound;
- retain a bound-device control send assertion to protect the shared surface,
  and assert a bound single-member device renders the same value/automation
  presentation as before the unification (the parity check).

Run the focused Device-control and shared-control-surface living verifies
identified by `docs/VERIFICATION.md`.
