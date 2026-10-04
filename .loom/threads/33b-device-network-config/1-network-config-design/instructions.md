# 1-network-config-design

**Status:** ready (`0` ruled 2026-10-04) · design gate
**Goal:** a written proposal for dashboard-managed Wi-Fi profiles, for Bob to
ratify. Read the parent for Bob's 2026-10-03 requirements (dev + hidden
performance networks, enable/disable).

## Scope from `0`'s ruling (`../0-lan-trust-review/ruling.md`)

Keep it low friction and simple — Bob, 2026-10-04.

- Profiles are provisioned **in the workshop** on a trusted network; plain
  transport there is fine. No secret encryption, keys or login.
- **Fleet-wide profile set** first; no per-device exceptions.
- **Priority** orders networks (e.g. show SSID1 > show fallback SSID2 >
  testing); **enable/disable** stays, so the easy-passphrase testing network
  can be switched off before bump-in.
- **Disable safely** shrinks to a warning when disabling or removing a network
  a device is on now. No timed rollback; recovery is physical.
- **Platform is out of this design** — decided in `2` with a device up.

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
- **Secrets:** storage and permissions on the device, redaction, listing
  without reading back. Transport is settled by `0`.
- **Privilege:** a narrow helper that can't take arbitrary files or commands.
- **Safe apply:** validation, ack timing, rediscovery, documented local
  recovery — including the warning for the network currently in use.
- **Wire:** `/admin` terms, exact-device targeting, idempotency, error phases,
  contract amendment. No passphrases in any broadcast or receipt.
- **UI:** placement, ordered list, masked input, warnings, active state, no-Wi-Fi
  devices, simulator parity.
- **Verification:** redaction tests, simulator, browser, and a real-Pi
  switch/reconnect/fallback/recovery gate.

## Deliver

`decisions.md` with the proposal and amendment text. After Bob ratifies: update
the parent, flesh out and resume `2`, tie this.
