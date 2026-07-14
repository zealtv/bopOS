# d8-4 results

The technical and facilitator view switches are now matching header buttons to
the left of their bopOS wordmarks. The managed audition relay now consumes the
selector-less `/cue` and `/pt` planes that it previously dropped: cues are held
against the dashboard's shared monotonic deadline, and authored point geometry
is decomposed independently for each virtual node's assigned elements before
the ordinary engine-facing `/cue` and `/pt` messages are sent.

Mixed-engine installations are recorded as a deferred complication in the
dashboard development context and current handoff. Managed simulation still
launches one homogeneous manifest/engine across all seats; no policy was added.

Verification:

- `verify_d8_sim_controls.py` passed 9/9 using the real Dashboard-managed
  audition child and two fake engine UDP sockets. It covered distinct point
  values, point release, scheduled cue payload/timing/fan-out, both header
  positions, and the deferred note.
- Retained d8-2 managed simulation passed 9/9.
- Retained ui-1 real dashboard/simfleet/Chromium layout suite passed all 10
  checks, including both directions of view navigation.
- The node-side seam-3 suite passed its six direct point decomposition checks,
  then hit its known pre-seat integration assumption (`device.id == 1`).
- The older audition-1c wrapper reached its no-engine test but expected `/hb`
  before the later-added `/audition/ready`; preview-1 likewise retains pre-seat
  assignment fixtures. These failures are unrelated superseded assumptions;
  the focused managed child and current d8-2 suite cover the changed path.
- Python compilation, JavaScript syntax, and `git diff --check` passed. No
  audible engine, installation hardware, or iPad/touch run was performed.
