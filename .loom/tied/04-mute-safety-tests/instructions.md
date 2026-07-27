# 04-mute-safety-tests

Promote the current, ratified mute-safety semantics into living tests.

- Treat `28-fleet-mute-semantics` and `29-fleet-patch-sync-hang/2-fix` as
  supersession context, not as evidence of a live defect.
- Cover effective output safety, convergence after heartbeat/restart, and the
  distinction between requested device state and fleet execution safety.
- Audit existing output-gate and device-enabled tests before extracting any
  tied assertion.
- Assert public state and behavior rather than exact command lists, copy, or
  private implementation shape.

Verify against production helpers and, where it adds value, simfleet. Record
what cannot be established without real audio hardware.
