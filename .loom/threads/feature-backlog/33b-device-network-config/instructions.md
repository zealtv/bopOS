# 33b-device-network-config

**Status:** parked by Bob, 2026-07-23 · Bob-gated design first
**Goal:** manage a Pi's saved Wi-Fi networks (multiple SSIDs + passphrases) from
the Device tab, like audio config.

Why it's gated: user-facing, writes privileged system config, handles secrets,
and can disconnect the very device being changed.

## Constraints

- Ordered saved profiles (SSID + passphrase): add, update, remove, reorder,
  active network.
- **Passphrases never leave the device** — not in OSC status, WebSocket state,
  logs, browser storage, simulator fixtures or repo files. UI may show "secret
  set".
- Routine apply is non-interactive; root work goes through a narrow provisioned
  helper.
- Staged validation, safe apply, reconnect, rollback/recovery — deleting or
  deprioritising the active network can cut the control path.
- Don't assume an interface name or that Wi-Fi exists.
- Keep secrets out of `bopos.config` unless the design proves it safe.

## Stitches

1. `1-network-config-design` — proposal for Bob.
2. `2-network-config-implementation` — placeholder until `1` is ratified.
