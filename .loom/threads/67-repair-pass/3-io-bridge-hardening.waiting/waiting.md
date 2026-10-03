# Waiting on Bob

The software repairs and regression tests pass (see verification.md).

Primary remaining gate: Bob's Finn Jet wrong-address LIS3DH hardware check;
explicitly pending and not claimed as verified.

The error-reply vocabulary in wire-proposal.md is no longer a gate here:
Bob moved it into `59-i2c-inventory/0a-io-design-review` (decision 1,
transport and errors) on 2026-10-03, since where IO errors go is part of that
design. The bridge keeps logging those cases until then.

Resume once these gates are resolved; do not tie the stitch on software-only
evidence.
