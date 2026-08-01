# 2-engine-admin-requests — notes

Implements the `/admin <action>` engine-sent request ratified in
`1-contract-amendment` (tied first, `2ee746b`).

## What changed

- `python/bopos.py`:
  - `ENGINE_ADMIN_VERBS` dict maps the four ratified action strings
    (`update-patch`, `update-bopos`, `shutdown`, `reboot`) to the existing
    `pull_active_patch_callback` / `update_bopos_callback` / `shutdown_callback`
    / `reboot_callback` functions — the same callbacks `PROVISION_VERBS` /
    `LIFECYCLE_VERBS` already use for the LAN `/os/*` verbs, reused verbatim
    (no duplicated logic).
  - `admin_callback(path, tags, args, source)` is the localhost 7770 handler:
    validates `args`, looks up the action, logs a warning and returns for a
    missing or unknown action (never fatal), otherwise dispatches via
    `run_admin_verb(callback, [], node_state)` on a daemon thread —
    `reply_socket`/`requester` default to `None`, so `run_admin_verb`'s
    `rev_reply` path is skipped safely (matches the "no selector, no reply to
    the engine" instruction; `run_admin_verb` already guards
    `reply_socket is None` for exactly this case).
  - Registered with `server.addMsgHandler("/admin", admin_callback)` beside
    the other 7770 handlers (`/config`, `/store`, `/load`, `/report`).
  - `report_reply`'s `contract_version` bumped `"1.6"` → `"1.7"`.
  - Updated the stale comment above `LIFECYCLE_VERBS` ("Engines cannot issue
    administrative commands") to name the bounded `/admin` exception.

- `tools/simfleet.py`: 7770 (and 6661) are not modeled at all by the
  simulator — they're per-node localhost channels between a real Pi's engine
  process and its own `bopos.py`, and the sim represents N devices inside one
  shared process answering the LAN wire (5550/6660) only; there is no
  per-device localhost port for N simulated engines to each bind, so there is
  no real "port" for a listener to accept `/admin` on (confirmed: no `6661`
  or per-device port anywhere in the file). Added `SimFleet.admin_request(
  device, action)` as the minimal analog: a direct call a verify harness
  drives (mirroring how `fire_cue` already logs cue fires instead of
  delivering them to a nonexistent engine), which logs `admin <action>` for
  the four known actions and `admin unknown-action=<action>` otherwise,
  and never executes anything (never shuts the laptop down) — same
  log-and-never-execute contract as `bopos.py`'s `admin_callback`.

- Did not touch any `.pd` file. The PD-side `[bopos]` bus plumbing that would
  let a patch actually send `/admin` from inside PD (e.g. a `to-bopos-admin`
  bus in `pd/bopos.pd`) is Bob's follow-up per house rules and per the
  contract-amendment stitch's note in §4.2.

## Verification

`verify_admin_requests.py` (browser-free, run with
`~/.venvs/bopos/bin/python`) — 15/15 checks pass:

- Imports the real `python/bopos.py` with `pyOSC3.OSCServer`/`OSCClient`
  faked before import (same technique as
  `.loom/tied/08-unbound-admin-seam/verify_uid_admin.py`), so no real UDP
  socket is bound and nothing can actually reboot/shut down the machine
  running the verify.
- Drives `bopos.admin_callback` directly for all four ratified actions plus
  an unknown action and a missing-args call; asserts each known action
  reaches its monkeypatched callback exactly once (via a background-thread
  wait) and that unknown/missing actions dispatch nothing and don't raise.
- Confirms `/admin` is registered on the 7770 handler map.
- Confirms `ENGINE_ADMIN_VERBS` entries are (`is`) the identical callback
  objects as `PROVISION_VERBS`/`LIFECYCLE_VERBS` — proves no logic
  duplication, not just equivalent behaviour.
- Confirms `admin_callback`'s default `reply_socket=None`/`requester=None`
  path runs to completion without raising.
- Confirms `report_reply` now reports `contract_version: "1.7"`.
- Imports `tools/simfleet.py` and drives `SimFleet.admin_request` directly
  (constructing a bare `SimFleet` via `__new__` + a fake `log`), confirming
  known/unknown actions are logged and nothing is executed.

Ran: `~/.venvs/bopos/bin/python .loom/threads/patch-admin-surface/
2-engine-admin-requests.stitching/verify_admin_requests.py` — `15/15 passed`.

## Honestly out of scope / not verified here

- Real Pi execution of `shutdown`/`reboot` via `/admin` is hardware
  verification: needs Bob or a live rig to confirm `request_power_action`
  actually powers a real device off/on when reached through this new path
  rather than the LAN `/os/*` path. Not exercised in this stitch.
- The PD-side bus that would let a real patch fire `/admin` is unbuilt (Bob's
  `.pd` follow-up), so there is no end-to-end PD → `bopos.py` path to drive
  yet; this stitch verifies the `bopos.py`-side contract only.
