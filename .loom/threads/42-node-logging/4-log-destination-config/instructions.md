# 4-log-destination-config

Log-destination choice, its admin surface, and the Device tab block.
Ratified design: `../1-logging-seed-design` (tied). Builds on
`2-nodelog-facility` (the `destination_dir()` seam) and
`3-usb-automount-install` (the `/media/bopos-usb` mount).

## Build

- **Model:** bounded choice `internal` (default, `~/bopos-logs/`) | `usb`
  (`/media/bopos-usb/bopos-logs/`). No free paths.
- **Persistence:** `LOG_DESTINATION=internal|usb` in `bopos.config`, next
  to the audio keys (`python/audio_config.py` CONFIG_KEYS is the pattern).
- **Effective resolution:** `usb` configured but stick absent ⇒ fall back
  to internal, visibly; never drop, never RAM-buffer; fallback files stay
  on the SD (ratified — no copy-on-insert). Hot insert starts new entries
  on the stick without restart (cheap per-open `ismount` check); removal
  degrades on next write.
- **OSC surface (contract amendment, additive, mirrors v1.11
  audio-config):**
  `/all/os/to <uid> log-config <json>` →
  `/os/log-config <uid> <ok|err> <json>`; request JSON
  `{"destination": "internal"|"usb"}`; receipt JSON is the complete log
  state object. Exact-UID physical administration.
- **Heartbeat:** device object gains
  `log: {destination, effective, usb_present}` (finalize shape here).
- **Device tab:** a "Logging" block — destination selector
  (Internal / USB), effective-state indication, USB presence.
  **UI specifics are a Bob gate:** show him the block before tying.
- **simfleet parity** for envelope, receipt, and heartbeat field.

## Verify

Headless Playwright + simfleet (`~/.venvs/bopos`; copy the newest tied
`verify_*.py` as template) for the Device tab block and envelope round
trip; durable wire/heartbeat assertions go into `tests/`. Real
stick-present behaviour on Ciro Toast is a hardware adoption check.
