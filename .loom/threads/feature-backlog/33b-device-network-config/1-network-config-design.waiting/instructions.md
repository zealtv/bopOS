# 1-network-config-design

**Waiting:** Bob moved the network-credential feature to `feature-backlog` on
2026-07-23. Resume only when he explicitly brings it back into active work.

Design saved-network configuration from the Device tab. Produce a written
proposal for **Bob to ratify**; do not implement past this gate.

## Decide

- **Profile model.** An ordered set of saved profiles with SSID and write-only
  passphrase. Define stable identity, priority/order, add/update/remove, active
  and last-successful state, duplicate SSIDs, and behavior when a secret is
  left blank during an edit.
- **First-slice bounds.** Decide support for open networks, hidden SSIDs, Wi-Fi
  country, per-profile security modes, Ethernet, DHCP/static addressing, and
  exact-device versus fleet application.
- **Platform owner.** Inspect supported Raspberry Pi OS images and choose the
  authoritative network manager and persistent store rather than assuming
  `wpa_supplicant`, NetworkManager, or a fixed interface name.
- **Secret boundary.** Define how write-only passphrases reach the exact
  selected device, storage and permissions at rest, redaction rules, and how
  the Dashboard lists profiles without reading secrets back. Include browser
  refresh, reconnect, deletion, and replacement behavior.
- **Privilege boundary.** Keep ordinary bopOS convergence unprivileged. Specify
  a narrow privileged helper/provisioning policy that cannot accept arbitrary
  files, shell, or commands.
- **Safe apply and recovery.** Define validation, staged activation,
  acknowledgement timing, network selection/fallback policy, rediscovery,
  timeout, rollback or a documented local recovery path. Account for edits
  that remove or deprioritize the network carrying the current connection.
- **Wire surface.** Define `/admin` request/outcome terms, exact-device
  targeting, idempotency, error phases, ordering semantics, and contract
  amendment. Passphrases must never appear in inventory/status broadcasts or
  outcome receipts.
- **Device-tab UI.** Specify placement beside device configuration, ordered
  profile list, add/edit/remove/reorder controls, masked secret input,
  confirmation/warnings, active/configured feedback, unavailable/no-Wi-Fi
  behavior, and simulator/audition parity.
- **Verification.** Identify browser-free security/redaction tests, simulator
  tests, Dashboard UI coverage, and the real-Pi switching, reconnect, fallback,
  and recovery gate.

## Deliverable

Add `decisions.md` here with the proposal and contract-amendment text. Record
Bob's ruling. Once ratified, update the parent, refine and un-`.waiting`
`2-network-config-implementation`, then tie this design stitch.
