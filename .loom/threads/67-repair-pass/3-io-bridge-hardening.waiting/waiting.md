# Waiting on Bob

The software repairs and regression tests pass (see verification.md).

Primary remaining gate: Bob's Finn Jet wrong-address LIS3DH hardware check;
explicitly pending and not claimed as verified.

Also pending: ratify the error names/reason vocabulary in wire-proposal.md
before implementing replies for malformed arguments, unknown IO dispatch, and
write failures. The existing error shape is retained; the contract is untouched.

Resume once these gates are resolved; do not tie the stitch on software-only
evidence.
