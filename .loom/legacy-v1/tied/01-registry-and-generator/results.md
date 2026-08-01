# Results

Implemented the non-UI device-alias foundation from the ratified design:

- `dashboard/device_aliases.py` ships pinned generator v1 with 64 global given
  names and 64 character-word surnames; `Freda` and `Sparks` are index zero.
- SHA-256 selects a full-cycle deterministic probe over all 4,096 pairs.
  Resolved records are persisted, so collisions never rename an existing box.
- `InstallationState` now owns a durable global `device_registry`, allocates
  aliases for older bound offline UIDs, exposes aliases as public projections,
  and excludes the registry from venue snapshots and venue loading.
- Custom alias validation is exactly two short ASCII alphabetic words with
  case-insensitive uniqueness. State methods provide atomic Rename and Reset
  foundations for the following UI stitch.
- Audition/virtual UIDs never enter the registry. Aliases do not enter runtime
  device records, Seats, hostname, node state or OSC.
- Forget refuses bound devices and atomically removes both runtime observation
  and registry entry for unbound devices. Bulk offline Forget does the same.

## Verification

- `verify_device_alias_registry.py`: **16/16 passed**, covering word-list lint,
  pinned vectors, collision ownership, custom validation, persistence, older
  state adoption, venue isolation, Reset, virtual exclusion, public projection,
  separation from runtime identity, bound refusal, genuine Forget and bulk
  Forget.
- Current Seats workspace real-dashboard browser suite: **12/12 passed**.
- Current Devices workspace browser suite reached **8/8 early checks passed**
  before the execution harness ended the longer run at its time ceiling; no
  alias assertion failed and no test process remained. Full cross-surface
  browser verification belongs to stitch 03.
- Python compile checks and `git diff --check` passed.
- Two older tied backend scripts expose pre-existing stale harness boundaries:
  `d8-1-seat-model` lacks the later `FakeOSC.unassign`, and `fetch-landing` was
  already recorded separately. They were not edited.

No hardware, audible, touch-device or screen-reader gate was run in this
foundation stitch. Word-list combination review remains explicitly owned by
stitch 03.
