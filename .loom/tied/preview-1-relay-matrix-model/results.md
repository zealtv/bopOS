# Preview relay and matrix convergence results

`tools/audition.py` now retains each virtual node's dashboard-owned identity,
name, and ordered element positions, consumes a loopback-only private listener
frame, and delivers the tied fixed-stereo matrix to each selector-stripped
engine port. Dashboard heartbeat catch-up replays durable full assignments to
ephemeral audition nodes, so a relay restart recovers positions without a new
drag. The fleet OSC contract and production helper are unchanged.

## Private surfaces and geometry

- Dashboard/localhost relay frame:
  `/audition/listener <x> <y> <heading-deg> <range-m>`.
- Engine frame: `/audition/matrix <l0> <l1> <r0> <r1>` (unchanged from the
  tied channel spike).
- Floor coordinates remain metres, top-left origin, +x right, +y down.
- Heading 0 degrees points map-up; positive angles turn clockwise.
- Listener-relative balance is the source direction dotted with the listener's
  right vector. Distance gain reuses `pointfield` smooth falloff with the
  explicit listener range. Coincident sources are centre/unity.
- Rear forward-bias is deliberately not frozen here. The later user-facing
  puck stitch may co-design an additional attenuation law without changing the
  relay or matrix seams.

Listener frames are accepted only from a loopback source and are full-state,
idempotent updates. Before the first valid listener, no private matrix is sent
and the proven PD load-time identity remains authoritative. Malformed listener
or assignment state holds the last valid state. Zero positions and unsupported
N>2 assignments produce safe identity while the complete ordered assignment is
still retained.

## Convergence

- Matching `/all/os/assign <uid> <id> <name> [x y]xN` updates one virtual node,
  pushes `/id`, sends its current complete matrix, and immediately heartbeats
  the converged id.
- Assignment or listener changes recompute immediately. Repeated listener full
  state resends all matrices.
- The normal heartbeat cadence resends current matrices after listener state
  exists, so a replacement engine listening on the same local port converges
  within one heartbeat interval.
- A known configured dashboard node appearing offline or with the wrong wire id
  receives its durable full assignment. The acknowledgement heartbeat cannot
  loop because the node is already online and advertises the configured id.
- `tools/simfleet.py` logs ordered assignment positions for preview regression
  observability but does not pretend to render audio.

## Verification

Focused real-UDP verifier (non-default localhost ports, real no-engine audition
relay plus real simfleet):

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/audition-rig/audition-2-listener-puck/\
preview-1-relay-matrix-model.stitching/verify_relay_matrix.py
preview relay matrix verify: 96 checks passed
```

It covers cardinal/rotated/coincident geometry, listener and assignment
validation/hold, loopback isolation, dashboard durable catch-up without loops,
initial identity safety, UID isolation, zero-based and changed ids + immediate
heartbeats, old/new selector behavior, ordered one/two-position matrices,
zero-position identity, listener recompute, rate-limited wrong-id replay,
periodic `/id` + matrix reconnect resend, existing parameter relay, honest
negative-message assertions, clean teardown, and simfleet ordered-position logs.

Compilation, tied model regression, and whitespace:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/audition_geometry.py python/audition_matrix.py tools/audition.py \
  tools/simfleet.py dashboard/osc_bridge.py \
  .loom/threads/audition-rig/audition-2-listener-puck/\
preview-1-relay-matrix-model.stitching/verify_relay_matrix.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/preview-0-channel-model-spike/verify_audition_matrix.py
audition matrix verify: 81 checks passed
git diff --check
```

Nearest Stage 0 integration regression:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/audition-1c-engine-boundary-adoption/verify_audition_boundary.py
PASS: v1.2 context, PD port override, relay isolation, and owned teardown
```

Socket-bearing verifies require permission outside the command sandbox. The
focused verifier's initial sandbox run failed at localhost `bind()` as expected;
the permitted runs above passed.

## Not verified or deferred

- No `.pd` or SC adapter was changed; actual engine consumption of the private
  OSC frame is the next adapter-integration stitch.
- No dashboard listener UI was added. Puck interaction, room-derived range,
  and any audible rear-bias choice stay in the later dashboard stitch.
- Periodic state delivery to UDP engine stubs is verified. The launcher still
  does not implement an engine process restart command; a replacement process
  on the same port converges, but process supervision itself is not claimed.
- No Mac/Linux three-engine audible sweep was run in this software stitch.
