# preview-1-relay-matrix-model

Integrate the tied fixed-stereo matrix model into `tools/audition.py` and prove
that dashboard-owned assignment state converges to every virtual engine's
private audition matrix. This is controller/relay work only: do not edit PD,
SC, the dashboard UI, or the fleet OSC contract.

## State and geometry

- Extend each `VirtualNode` with its ordered element positions. Apply matching
  `/all/os/assign <uid> <id> <name> [x y]xN` messages locally as idempotent
  full state: validate and retain the complete true-N position list, update the
  node id/name, push `/id`, and heartbeat the converged identity immediately.
  The fixed-stereo preview safely bypasses assignments with more than two
  positions; it does not truncate or corrupt their fleet assignment state.
- Retain one audition-local listener state (position + heading) in the relay.
  Define and test the coordinate/heading convention and a bounded pure mapping
  from listener/element geometry to the tied model's `(balance, gain)` inputs.
  Unpositioned nodes remain exact identity bypass.
- Accept listener updates only on a private audition address delivered locally;
  do not add it to `docs/OSC-CONTRACT.md` or production `bopos.py`.

## Matrix convergence

- Send one complete `/audition/matrix <l0> <l1> <r0> <r1>` frame to the
  selector-stripped local engine port. Never send partial/per-element gains.
- Recompute immediately after a matching assignment or listener update.
  Resend current identity and matrix state on engine catch-up/heartbeat so a
  restarted or reconnected engine converges without another dashboard edit.
- Before valid listener state, send no preview state; the engine's proven
  load-time identity bypass remains authoritative. Invalid listener or
  assignment messages retain the last valid state.

## Observability and verification

- Give `tools/simfleet.py` ordered assignment-position logging for preview
  convergence, but do not simulate an audio adapter or advertise a production
  capability. Real UDP engine stubs observe the complete matrix frames.
- Add a stitch-local browser-free verifier using real UDP datagrams on
  non-default ports. Cover assignment uid matching/isolation, ordered 0/1/2
  position state, identity changes + immediate heartbeat, listener validation,
  exact matrix values/order, assignment/listener recomputation, catch-up resend,
  malformed-state hold, and no regression to ordinary selector relay.
- Compile touched Python, run the focused verifier, the tied preview-0 matrix
  verifier, and the nearest Stage 0 audition boundary regression. Record exact
  commands/results and all unverified audio/dashboard/SC boundaries.
