# Handoff — Seats tied; Devices workspace next (2026-07-15)

State at handoff: the accepted tabs next sweep is complete through the
Seats/UID boundary runway (01, 02, 03, 05, 06, 08, then 07). Loom has
104 tied stitches, 6 dropped stitches, no claim, and no loose end because the
remaining next-sweep stitches are deliberately `.waiting`. The worktree is
clean at `7d8e3a0 Make Seats the assignment workspace` before this handoff-note
commit.

## Start the next session here

1. Read `CLAUDE.md`, this handoff, and run `./.loom/loom.sh status`.
2. Read:
   - `.loom/threads/ui-tabs/tabs-3-next-sweep/09-devices-workspace.waiting/instructions.md`
   - `.loom/tied/06-seat-device-boundary-design/{proposal.md,ratification.md}`
   - `.loom/tied/07-seats-workspace/verification.md`
   - `.loom/tied/08-unbound-admin-seam/results.md`
3. Resume the intentionally waiting stitch with
   `./.loom/loom.sh claim 09-devices-workspace` and work only that stitch.
4. Implement one physical-device roster and predictable bound/unbound detail:
   identity, health/version, report, direct Identify, guarded individual
   actions, Shutdown All, a binding shortcut, content drift, and one-click
   repair. Remove duplicate roster presentation, Seat authoring, and mix params
   from Devices.
5. Retain the noun boundary: Seats alone owns Seat name/ID/geometry and the
   authoritative assignment transaction. Device-side binding shortcuts must
   call the same safe server transaction; do not reintroduce direct mutation.
6. Add a focused real-dashboard Playwright verifier and tie 09 before touching
   10.

## What landed in this session

- `69ac003` — live state coherent after audition transitions (01).
- `4795ee6` — bounded patch-switch terminal state (02).
- `c07a49d` — Seat identity distinct from devices (03).
- `380bf5d` — explicit Live fleet / Simulation / Patch edit target (05).
- `c56be47`, `8f04148` — Seat/Device boundary proposed and ratified (06).
- `4002ca7` — UID-targeted unbound administration and `unassign` handshake (08).
- `7d8e3a0` — dedicated Seats workspace and safe assignment transactions (07).

Stitch 07 now provides create/delete/name/reindex/position, room/points/venues,
map-first Identify/Assign, strict one-Seat-per-UID ingress, exact venue
preflight/commit rollback, and online/offline revocation ordering. Devices keeps
device diagnostics but no editable Seat geometry or mix parameters.

## Important transaction invariants for 09+

- `seat.bound` is the sole dashboard-authoritative Seat↔physical UID edge.
- All Seat/venue mutations serialize under `Dashboard.supervisor_lock`.
- An online changed UID must acknowledge UID `unassign` with heartbeat `id=-1`
  before dashboard mutation. Timeout means no dashboard state change.
- When a binding move changes both target occupant and source UID, both online
  nodes revoke before commit. Partial failure replays current assignments.
- Known offline displaced/moved nodes retain `revoking_assignment=true`; on
  reconnect the bridge UID-unassigns them, waits for `id=-1`, then replays any
  newly durable Seat assignment. They are unavailable to UI/backend binding
  while revoking.
- Seat IDs are strict non-negative integers. Installation, CSV, and venue
  ingress reject duplicate IDs/UIDs and non-string `bound` values.
- Reindex migrates current preset references atomically. Saved venues remain
  explicit snapshots. Deleting a Seat removes its current preset references.
- Production points remain runtime-only and do not persist with venues.
- Never edit `.pd` files.

## Verification state

The tied 07 artifacts retain two reviewed screenshots and exact commands:

- focused state/server/bridge/UI suite: 15/15 passed;
- real server + two-node simfleet Playwright suite: 12/12 passed;
- Python compile, JavaScript syntax, and `git diff --check` passed;
- no real hardware, packet-loss, iPad/touch, or audible gate was claimed.

The tied UID-admin suite reports 23/24 under the new model only because its old
out-of-band `/all/os/assign` expectation is now deliberately quarantined and
UID-unassigned. Stitch 07's browser verifier proves ordinary assignment through
the authoritative Seat transaction. Several older browser verifies reference
replaced selectors (`#device-bind`, `#simulate-toggle`) or pre-quarantine
unbound IDs; use the stitch-local 07 suites as authority for those seams.

## Launch and environment

- Disk space is healthy at handoff (about 121 GiB available).
- A dashboard process was previously observed on port 8080 during this session,
  but process inspection later became unavailable; confirm in the new session
  before relying on it. Do not assume it is running current code.
- Localhost/UDP browser verifies may need sandbox escalation.
- No `.pd` file was edited.
- After committing this handoff, the worktree should be clean and there should
  be no claimed stitch.

## Remaining accepted sequence

1. `09-devices-workspace`
2. `10-patches-fleet-workflow`
3. `11-assets-fleet-workflow`
4. `12-dashboard-live-controls`
5. `13-diagnostic-density`
6. `14-device-alias-design`
7. Resume `patch-workflow-friction/friction-0..1` after the next sweep.

The full accepted plan remains
`.loom/tied/tabs-2-review-session/next-sweep-proposal.md`.
