# 4-log-destination-config — verification

Log-destination choice, its admin surface, and the Device-tab block, per the
ratified design (`.loom/tied/1-logging-seed-design/` §3). Builds on the stitch-2
`destination_dir()` seam and the stitch-3 `/media/bopos-usb` mount.

**Bob gate cleared 2026-07-24** — Bob reviewed the `logging-block.png`
screenshot and approved the Device-tab "Logging" block as-is. PD-side
`to-bopos-log` bus is in place (Bob's working-tree `.pd` edits this session).
Stitch tied. Everything below is implemented and software-verified; the real-USB
behaviour remains the Ciro Toast hardware adoption check (Bob has hardware ready
to run it live).

## What landed

- **`python/log_config.py`** — bounded model + effective resolution:
  `internal` (default `~/bopos-logs/`) | `usb` (`/media/bopos-usb/bopos-logs/`),
  no free paths. `configured`, `usb_present` (`os.path.ismount`), `effective`
  (usb only if chosen *and* mounted), `effective_dir`, `status_object`
  (`destination`/`effective`/`usb_present`), `validate`, and an atomic
  `update_config_file` that sets `LOG_DESTINATION` while preserving other
  `bopos.config` text.
- **`bopos.py`** —
  - configures nodelog's destination hook to `log_config.effective_dir(node_state.config)`,
    resolved per entry → hot USB insert/remove takes effect on the next write,
    with visible fallback to internal (never dropped, never RAM-buffered);
  - `apply_log_config` on the `/all/os/to <uid> log-config <json>` surface:
    validates, persists, reloads config, replies
    `/os/log-config <uid> <ok|err> <json>` (no engine restart, no rollback);
  - `log_report` + `"log"` added to `/os/report`;
  - **fix:** `read_node_config` now allowlists `LOG_DESTINATION` (default
    `internal`) — without it the persisted choice never loaded back;
  - `bopos.config.example` seeds `LOG_DESTINATION=internal`.
- **Dashboard** — `osc_bridge.set_log_config` + timeout + `/os/log-config`
  reply handler (stores `report.log`, sets `log_apply`); `server.py`
  `set_log_config` mutation (online + bounded destination gate); `dashboard.js`
  `logSection`/`bindLogControls` with a `logDestinationDrafts` map so an unsaved
  selection survives heartbeat re-renders (same pattern as `seatBindingDrafts`);
  `style.css` `.log-config-row`/`.log-state`. The block shows the destination
  selector (Internal / USB), the effective state, USB presence, and the
  fallback ("USB not mounted, logging to internal storage").
- **simfleet parity** — `device.log_destination`/`usb_present`, `device_log_state`
  (effective fallback), `"log"` in `/os/report`, and the `log-config` uid-admin
  handler emitting `/os/log-config`.
- **Contract v1.13** — additive §6 envelope + the exact-device log-configuration
  paragraph + `log` in the `/os/report` facts + §15 row, mirrored in
  `OSC-REFERENCE.md`. Reported `contract_version` bumped 1.12 → 1.13 in
  lockstep (bopos/simfleet/audition + the three pinning tests).

## Verified (software)

- **Unit** — `tests/test_log_config.py` (12): bounded model defaults, effective
  usb-only-when-mounted, status shape, validate accept/reject, config-file set
  + preserve + idempotent replace + refuse-invalid, node apply persists +
  replies ok with visible internal fallback, invalid → err + nothing persisted,
  dispatch routes the verb, simfleet effective fallback. Full non-browser suite
  **83 pass**.
- **Browser** — `tests/verify_log_destination.py` (real dashboard + fake
  physical peer, `--sim-no-engine --sim-audio-backend none`), 5 checks pass:
  the block renders selector + effective state; the USB choice sends the exact
  `/all/os/to <uid> log-config {"destination":"usb"}` envelope; the receipt
  records destination usb with `effective:internal`/`usb_present:false`; the
  fallback is surfaced to the operator; no page errors.

## Bob gate (why `.waiting`)

The Device-tab "Logging" block UI is a Bob gate at implementation review. The
proposal fixed only what it must convey (destination selector, effective state,
USB presence); the visual specifics are his to ratify. See `logging-block.png`.

## Not verified here (hardware adoption check — Ciro Toast)

Real `usb` write to a mounted stick under `/media/bopos-usb/bopos-logs/`,
unprivileged FAT write permission, and hot insert/remove taking effect on the
next entry. Software models the fallback and the per-entry resolution.
