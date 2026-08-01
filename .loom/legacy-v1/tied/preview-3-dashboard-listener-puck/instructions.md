# preview-3-dashboard-listener-puck

Put the tied listener geometry under direct control on the existing dashboard
spatial map. This is an audition-only control seam: do not add the listener to
the ratified fleet OSC contract or compose preview gains in the dashboard.

## Dashboard UI and state

- Draw one clearly distinct listener puck inside the room, including a visible
  heading indicator. Dragging moves x/y; provide a numeric heading control.
- Use installation metres (origin top-left, x right, y down), heading 0 = map
  up, positive clockwise. Clamp position to the current room, normalize heading
  modulo 360, and require a finite range greater than zero.
- Retain the current valid x/y/heading with the room and include it in the
  initial WebSocket state. Derive preview range from the positive room diagonal
  when shaping the private four-value frame; do not create a second range state
  that can drift after a room edit.
- Stream bounded movement updates during a drag and send the final exact state
  on release. Preserve the existing device and point drag behavior.

## Private relay seam

- Add a dashboard WebSocket command for the complete listener state. The server
  validates atomically, broadcasts the accepted state to connected browsers,
  and sends `/audition/listener <x> <y> <heading-deg> <range-m>` directly to
  loopback port 6660 through the existing OSC bridge socket.
- Never broadcast that private frame onto the installation LAN. Keep
  `tools/audition.py`'s loopback-source rejection intact.
- Resend the current listener when an audition node appears/reappears so a
  restarted relay catches up. A loopback-only audition-ready frame may request
  this dashboard-owned full-state replay without weakening ordinary heartbeat
  replay limits. Existing full `/os/assign` frames remain the
  authority for ordered element positions; listener movement and position or
  element-count edits must each produce a fresh complete engine matrix.
- Keep normal simfleet/production devices unaffected. Add only the minimum
  preview observability needed by focused verification; do not invent a fake
  audio engine or public protocol.

## Verification

- Add a focused browser + UDP integration verifier using the established
  dashboard Playwright harness. Prove puck rendering, drag, heading/range edits,
  invalid-state retention, loopback-only listener delivery, one/two/zero
  position matrix convergence, browser reconnect state, and relay restart
  catch-up.
- Run the tied preview-1 relay verifier plus the nearest spatial-map and
  assignment regressions. Record exact checks and honest browser/audio/platform
  boundaries before tying.

## Done

Moving the listener puck or editing heading/range immediately moves the audible
preview through complete engine matrices; device position-count edits converge
without another puck gesture; reconnects restore state; and production fleet
traffic and the ratified OSC surface remain unchanged.
