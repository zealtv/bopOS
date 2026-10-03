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


## Device-agnostic (Bob, 2026-10-03)

Finn Jet and Ciro Toast are out of date and will be updated first. Run this
check on any current bopOS device unless the test needs specific hardware;
the hardware need here is noted above (e.g. a device with that peripheral or
card). Record which device and its framework revision.
