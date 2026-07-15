# Read-only design review

An independent read-only pass checked the draft against `dashboard/state.py`,
`dashboard/server.py`, `python/bopos.py`, and `docs/OSC-CONTRACT.md`. No reviewer
edits were made.

Findings incorporated into the proposal:

- Dashboard-only unbind/replacement leaves the displaced node's persisted ID
  live and can create duplicate selectors. The revision adds an attributable
  UID-targeted unassign handshake and makes it a dependency of Seats mutations.
- `seat.bound` is dashboard-authoritative, while node persistence is explicitly
  a convergence replica needed for standalone operation.
- The one-to-one binding invariant now applies to every load/import ingress.
- The initial UID envelope excludes query families without uid-correlated
  replies and specifies allowlisted direct dispatch with per-verb validation.
- Reindex now defines malformed/missing preset handling, collision behavior,
  full pre-validation, atomic disk replacement and post-commit convergence.
- Saved venue loads explicitly restore snapshot IDs while applying binding
  validation and live-node revocation.

