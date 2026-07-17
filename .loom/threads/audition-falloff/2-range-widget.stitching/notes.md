# 2-range-widget notes

Implemented the pinned design: the listener heading widget's pull-out tip
distance now sets both `heading` (unchanged) and `range` (audible falloff
distance), persisted on the listener object through state, websocket
broadcast, and installation persistence.

## Changes

- `dashboard/state.py`:
  - Added `InstallationState.room_diagonal()` (factored out of the previous
    inline `math.hypot(width, depth)` in `default_listener`/callers) and
    `LISTENER_RANGE_MIN = 0.5`.
  - `default_listener()` now includes `"range": room_diagonal()` -- exactly
    today's behaviour for any listener that hasn't been dragged.
  - `clean_listener()` validates/clamps `range` to `[0.5, room diagonal]`.
    Missing, non-numeric, non-finite, or boolean `range` values fall back
    to the room diagonal (the historical fixed-diagonal behaviour), so
    older persisted installations and in-flight edits that don't touch
    range sound unchanged until someone drags the tip.
- `dashboard/osc_bridge.py` `send_audition_listener()`: sends the
  listener's own `range` in the 4-value `/audition/listener` frame instead
  of always computing the room diagonal; falls back to the diagonal if
  `range` is missing/invalid (defence in depth -- `clean_listener` should
  already guarantee a valid range by the time this runs, but this keeps
  the frame always well-formed even if `state.data["listener"]` were ever
  set another way). Frame shape is unchanged: still 4 floats
  (x, y, heading, range_m).
- `dashboard/static/js/spatial.js`:
  - Added `LISTENER_RANGE_MIN = 0.5` (module constant, mirrors the
    server-side floor for the client-side clamp during drag).
  - The listener puck's heading line/tip now render at `listener.range`
    (falling back to the room diagonal if absent) instead of the previous
    fixed `0.72` radius, so the widget visually reads as "how far I can
    hear."
  - The `headingDrag` pointermove handler now computes `listener.range =
    clamp(distance-from-listener-centre, 0.5, room-diagonal)` alongside
    the existing heading angle, and the tip is drawn at that clamped
    range. The tip's own hit-circle radius (`r: 0.12`, unchanged) is
    already independent of the drag distance, so the hit target stays
    usable at the 0.5m floor without extra styling.
  - `/audition/listener` frame shape unchanged (still 4 values); no
    changes to `tools/audition.py` were needed (same reasoning as
    1-forward-bias: it only consumes the frame as opaque geometry via
    `audition_geometry`, doesn't assume a fixed range).

## Design call made in-session (not itself ambiguous, but worth recording)

The pinned default (room diagonal) commonly renders the tip well outside
the visible room on load, since real rooms are usually much smaller than
their own diagonal-times-something layout -- this is the literal, intended
consequence of "the tip's distance from the listener centre IS the range"
combined with "default ... is the room diagonal." It's not a contradiction
of the pinned design, just a consequence of it, and the instructions only
call out keeping the hit-target usable when range is *small* (not when the
default happens to place it off-canvas). For the interactive Playwright
drag tests, testing a drag that *starts* from an off-screen tip is not
practical (Playwright/pointer-capture testing needs the initial
pointerdown to hit-test a genuinely on-screen element), so the fixture's
initial listener starts with `range: 1.5` (on-screen, mid-room) rather than
the diagonal default. The pure-Python `pure_state_contract_tests()` in the
verify script separately proves the diagonal-default behaviour directly
against `state.py`, so the default-on-load behaviour is still exercised,
just not through a browser drag starting from that exact position.

## Verification

`.loom/threads/audition-falloff/2-range-widget.stitching/verify_range_widget.py`,
run twice with `~/.venvs/bopos/bin/python` (both green, 15/15 checks):

- Browser-free `pure_state_contract_tests()`: `default_listener` range is
  the diagonal; `clean_listener` fills in a missing range with the
  diagonal; clamps a too-small range to 0.5; clamps a too-large range to
  the diagonal; passes a valid mid-range value through unchanged; falls
  back to the diagonal for non-numeric/boolean range.
- Playwright/subprocess: launches the real `dashboard/server.py` (
  `--sim-no-engine`) against a small fixture room (width 4, depth 3 --
  an exact 3-4-5 triangle, diagonal 5.0m, chosen so the drag targets
  needed to exceed/undercut the clamp bounds stay small in pixels and
  robust across viewport sizes) with one seat, enables simulation over the
  websocket directly (`ws.send('set_simulation', {active:true,
  confirmed:true})`, sidestepping the UI's `confirm()` dialog), waits for
  the simulation-gated `#spatial .listener-tip` to render, then:
  - drags the tip diagonally outward past the room diagonal and asserts
    the broadcast `installation.listener.range` clamps to exactly 5.0 and
    heading also changed;
  - drags the tip back to within 0.2m of the listener centre and asserts
    `range` clamps to exactly 0.5;
  - asserts the listener object still carries exactly the 4 frame fields
    (`x, y, heading, range`) -- no extra fields leaked in;
  - reconnects (fresh page load) and confirms the clamped range survived
    the round trip through the server's durable state;
  - independently reloads the on-disk `installation.json` via
    `InstallationState` after the server process exits and confirms the
    persisted range matches.

Followed the three documented Playwright gotchas: scrolled to (0,0) before
the spatial drag; drag targets are computed from measured on-screen scale
(`room_box` bounding box in px / metres) rather than fixed pixel guesses,
and the outward target is placed well inside the 1400x1400 viewport
(diagonal * 0.78 per axis, so the combined magnitude exceeds the room
diagonal without needing an extreme overshoot); a single type-aware
`page.on("dialog", ...)` handler is installed (prompt -> accept(""),
else -> accept()), though this test doesn't happen to trigger any dialogs
since it uses raw `ws.send` for `set_simulation` rather than the UI button.

No changes to `tools/simfleet.py`, `docs/OSC-CONTRACT.md`,
`docs/OSC-REFERENCE.md`, `docs/PORTS.md`, `python/bopos.py`, or
`python/runcontext.py` -- out of scope for this stitch and owned by the
concurrent agent's thread per the session's file-ownership split.
