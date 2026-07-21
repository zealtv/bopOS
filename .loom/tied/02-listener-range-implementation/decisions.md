# Decisions — 02-listener-range-implementation

Built exactly the design ratified in `01-listener-range-design` (alternative
A + D) with Bob's five rulings: 2.5x relative scrub gain, room-diagonal ceiling
kept (no server change), 0.9 m heading handle in metres, listener bar in the map
toolbar, residual tick retained.

## Implementation calls made inside the ratified design

1. **Signed radial travel, not raw pointer distance.** The proposal wrote
   `range += Δdistance × gain`, where `distance` is the pointer's distance from
   the listener. Read literally that caps an *inward* gesture at the collar
   radius (0.45 m → at most −1.1 m of range per drag) and turns to nonsense once
   the pointer crosses the dot. The scrub therefore records the radial direction
   the collar was pressed on and reads travel as the **signed projection onto
   that grab axis**. Outward it is identical to the proposal; inward it keeps
   shrinking past the dot, which is what "push/pull" has to mean. Gain, clamp
   and feel are unchanged.

2. **Focus survives re-render.** `render()` rebuilds the whole SVG on every
   heartbeat, so arrow-key control of the puck worked exactly once. `render()`
   now restores focus to the listener puck if it held focus before the rebuild.

3. **Ring drawn as two circles, not a split arc.** The "solid inside the room,
   dashed outside" outline is an unclipped dashed circle with the room-clipped
   solid circle drawn on top at the same radius — visually identical to arc
   splitting, and it survives any room shape without arc maths.

4. **Extra transparent hit circles** (`.listener-collar-hit`,
   `.listener-tip-hit`, 16 px non-scaling transparent stroke) give the ≥44 px
   touch targets the proposal asked for without visual weight.

## Superseded guard repaired

`.loom/tied/2-range-widget/verify_range_widget.py` pinned "dragging the tip
outward clamps range to the room diagonal" and "dragging the tip outward also
updates heading" — both of which this stitch deliberately reverses (the tip is
now a pure heading handle). Per CLAUDE.md the guard was **repaired in place**,
not left red: the two range assertions now drive the collar scrub, and the
heading assertion is inverted to "scrubbing the collar leaves heading alone",
with an inline comment naming this stitch. Everything it actually protects
(the [0.5 m, diagonal] clamp, the 4-value frame, persistence, reconnect) is
unchanged and still passes.

## Pre-existing failures not caused here

`.loom/tied/07-seats-workspace/verify_seats_workspace.py` fails 3 of 15 on
`main` (`test_offline_moved_binding_revokes_then_assigns_on_reconnect`,
`test_stale_unbound_heartbeat_is_quarantined_until_minus_one`,
`test_devices_detail_has_no_editable_seat_or_parameter_surface`). All three
scrape `dashboard/js/dashboard.js` text or exercise `osc_bridge` binding — none
touch `spatial.js`, `style.css` or the listener. Unrelated to this stitch;
noted alongside the loose `23-waveform-marker-guard-regression` finding.

## Not touched

`dashboard/state.py:733` — the server clamp stays as-is, per ruling 2. The wire
is unchanged: `set_listener` still carries exactly `x`/`y`/`heading`/`range`
(asserted).
