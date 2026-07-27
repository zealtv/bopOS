# 05-identity-and-fingerprint-tests

Promote durable identity and content-fingerprint invariants into living tests.

- Cover canonical UID/assignment behavior and patch/asset fingerprint
  comparison at their owning code surfaces.
- Audit existing device, patch-routing, and asset-context tests before mining
  `fp-*`, seat-model, or identity tied guards.
- Prefer real production models/helpers over drifting test doubles.
- Test additive wire evolution by property; do not pin complete verb lists or
  obsolete contract-version literals.
- Keep derived drift reporting non-blocking, consistent with the ratified
  entity architecture.

Record focused results and any honest hardware or network boundary.
