# 01-registry-and-generator

Build and verify the non-UI device-alias foundation.

- Add a globally durable `device_registry` keyed by UID and excluded from venue
  snapshots and virtual devices.
- Ship generator v1 with `Freda` and `Sparks` at index zero, at least 64 curated
  ASCII-only global given names and 64 short character-word surnames.
- Implement pinned SHA-256 candidate vectors, deterministic collision probing,
  immediate persistence, restart/offline resolution, atomic rename/reset, and
  genuine registry deletion for Forget.
- Validate custom aliases as exactly two short ASCII alphabetic words and
  enforce case-insensitive uniqueness in the backend.
- Add a focused browser-free verifier for persistence, venue isolation,
  collision/edit/reset/Forget behaviour, word-list linting and absence of
  alias leakage into runtime/node assignment state.

Do not change dashboard presentation in this stitch beyond exposing alias data
needed by the following UI child.
