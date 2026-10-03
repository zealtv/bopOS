# 1-network-config-design

**Status:** after `0-lan-trust-review` · design gate
**Goal:** a written proposal for dashboard-managed Wi-Fi profiles, for Bob to
ratify. Read the parent for Bob's 2026-10-03 requirements (dev + hidden
performance networks, enable/disable).

## Decide

- **Profiles:** identity, priority, add/update/remove, **enabled/disabled**,
  **hidden SSID**, active vs last-successful, duplicate SSIDs, blank secret on
  edit = keep.
- **Fleet vs device:** push one profile set to the whole fleet, and per-device
  exceptions if any. Where profiles live once `66-projects` lands.
- **Disable safely:** disabling the network devices are on right now must not
  strand them — say what happens (switch to the next enabled network first?
  refuse? timed rollback?).
- **First-slice scope:** open/hidden networks, Wi-Fi country, security modes,
  Ethernet, static IP, single device vs fleet.
- **Platform:** which network manager the supported Pi OS images actually use
  (don't assume `wpa_supplicant` / NetworkManager / `wlan0`).
- **Secrets:** how a passphrase reaches exactly one device — using `0`'s
  ruling — storage and permissions, redaction, listing without reading back.
- **Privilege:** a narrow helper that can't take arbitrary files or commands.
- **Safe apply:** validation, staging, ack timing, fallback, rediscovery,
  timeout, rollback or documented local recovery — including removing the
  network currently in use.
- **Wire:** `/admin` terms, exact-device targeting, idempotency, error phases,
  contract amendment. No passphrases in any broadcast or receipt.
- **UI:** placement, ordered list, masked input, warnings, active state, no-Wi-Fi
  devices, simulator parity.
- **Verification:** redaction tests, simulator, browser, and a real-Pi
  switch/reconnect/fallback/recovery gate.

## Deliver

`decisions.md` with the proposal and amendment text. After Bob ratifies: update
the parent, flesh out and resume `2`, tie this.
