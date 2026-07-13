# Listener puck results

The dashboard spatial map now owns one venue-relative listener perspective.
The white puck drags in installation metres and its heading control follows the
tied convention: zero points map-up and positive degrees turn clockwise.

## State and private seam

- Listener x/y/heading are sanitized atomically, clamped/normalized, persisted
  with the room, and restored in the initial WebSocket state.
- Preview range is derived from the finite positive room diagonal, so it cannot
  drift from a resized or loaded room.
- The dashboard shapes the complete private
  `/audition/listener <x> <y> <heading> <range>` frame and sends it only to
  `127.0.0.1:<send-port>`. Normal OSC messages keep their configured LAN target.
- `tools/audition.py` announces a private `/audition/ready` frame directly to
  the dashboard's loopback report port. The dashboard replies with all current
  audition assignments plus listener state, covering fast relay restarts that
  do not cross the ordinary 30-second offline threshold.
- Browser reconnects replay the complete listener. Identical full-state frames
  intentionally resend matrices; malformed listener state retains the last
  valid state and emits nothing.
- Existing `set_position` and `/os/assign` full-state paths handle live zero,
  one, and two-position changes. No listener term was added to the fleet OSC
  contract, and simfleet does not pretend to render audio.

## Verification

Focused real-dashboard, real-audition-relay, engine-UDP-stub, and Playwright
gate:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/audition-rig/audition-2-listener-puck/\
preview-3-dashboard-listener-puck.stitching/verify_listener_puck.py
listener puck verify: 21 checks passed
```

It proves explicit loopback ready delivery even with a broadcast heartbeat
target; malformed persisted-room fallback; initial one/zero-position matrices;
puck render, drag, heading, and malformed retention; room clamp plus derived
range; robust tray-to-room and room-to-tray assignment gestures;
zero/one/two-position convergence; browser reconnect matrix replay; and fast
relay restart catch-up.

Nearby audition and spatial regressions:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/preview-1-relay-matrix-model/verify_relay_matrix.py
preview relay matrix verify: 96 checks passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/spatial-map/verify_spatial.py
spatial checks passed
```

The historical `dashboard-3-discovery-assign/verify_assign.py` passed 10 of 11
checks but its placement gesture never reached the application: after later
spatial controls increased the map height, its `scrollTo(0,0)` left the tray
source at y=1102 in a 960px viewport. A diagnostic run that scrolled the source
into view and re-read both bounding boxes passed unchanged, including a drop
directly over the listener puck. The focused verifier retains the corrected
scroll/re-read gesture and exercises the same full assignment convergence; no
production hit-testing change was needed. Historical tied artifacts were
restored after the runs.

Compilation and static checks:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/state.py dashboard/osc_bridge.py dashboard/server.py \
  tools/audition.py verify_listener_puck.py
node --check dashboard/static/js/spatial.js
node --check dashboard/static/js/dashboard.js
git diff --check
```

## Boundaries

- Chromium was headless on macOS; no iPad/touch pass was run.
- UDP matrices were decoded and checked against the tied pure model, but this
  stitch did not run real PD/SC engines or claim an audible sweep.
- Three-engine audible Mac/Linux puck movement remains the next and final gate.
