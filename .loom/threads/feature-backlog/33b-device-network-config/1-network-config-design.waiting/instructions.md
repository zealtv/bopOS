# 1-network-config-design

**Status:** waiting — resume only when Bob brings it back · design gate
**Goal:** a written proposal for Device-tab Wi-Fi profiles, for Bob to ratify.

## Decide

- **Profiles:** identity, priority, add/update/remove, active vs
  last-successful, duplicate SSIDs, blank secret on edit = keep.
- **First-slice scope:** open/hidden networks, Wi-Fi country, security modes,
  Ethernet, static IP, single device vs fleet.
- **Platform:** which network manager the supported Pi OS images actually use
  (don't assume `wpa_supplicant` / NetworkManager / `wlan0`).
- **Secrets:** how a passphrase reaches exactly one device, storage and
  permissions, redaction, listing without reading back.
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
