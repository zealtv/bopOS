# Decisions — logging seed design (ratified by Bob, 2026-07-24)

Bob ratified `proposal.md` in full, answering all six open questions:

1. **Format:** plain text TSV — `timestamp<TAB>stream<TAB>values…`,
   ISO-8601 local time with offset, node-stamped at receipt. Not jsonl.
2. **File granularity:** per-stream daily files (`<stream>-YYYY-MM-DD.log`).
   Daily files are the rotation; defensive 50 MB per-file cap.
3. **Fallback files:** when `LOG_DESTINATION=usb` but no stick is mounted,
   entries fall back to internal (`~/bopos-logs/`) and **stay on the SD**
   — no copy-on-insert catch-up in v1. Never drop, never RAM-buffer.
4. **PD bus name:** `to-bopos-log`, consumed by `[bopos]` — Bob's patch
   edit (recorded in `.notes/pd-edits-for-bob.md`).
5. **Mount path:** `/media/bopos-usb` — bopOS-owned udev rule + systemd
   template unit, one stick, first partition, FAT-family with uid + flush.
6. **Interval encoding:** the patch author's responsibility — send a
   computed interval (safe to ~100 s at ms precision in PD floats) or raw
   events for node-exact timestamps.

Everything else stands as proposed: the `nodelog.py` facility and stream
model, the additive §4.2 `/log <stream> <values…>` engine-sent term on
7770, the bounded internal/usb destination persisted as `LOG_DESTINATION`
in `bopos.config`, the `log-config` exact-UID envelope + receipt mirroring
audio-config, the heartbeat `log` object (configured/effective/usb_present),
the Device tab Logging block (UI specifics remain a Bob gate at
implementation review), write-only-v1 (no dash log browsing), and the v1
exclusions list.

Anchor use case: Ciro Toast standalone — i2c buttons, headphone line-out,
time between two button presses logged for third-party retrieval by
pulling the USB stick (power off, remove, copy, reinsert). SSH stays
install-only.

## Implementation children laid out from this ratification

- `2-nodelog-facility` — facility + `/log` wire + contract amendment +
  simfleet parity + `tests/`.
- `3-usb-automount-install` — udev rule + systemd unit + idempotent
  `install-device.sh` step.
- `4-log-destination-config` — persistence, envelope/receipt, heartbeat,
  Device tab block (UI Bob gate), verifies.
- Bob's PD edit (`to-bopos-log` bus) is tracked in
  `.notes/pd-edits-for-bob.md`, not a stitch.
