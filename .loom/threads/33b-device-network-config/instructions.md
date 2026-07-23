# 33b-device-network-config

**FEATURE.** Manage a Raspberry Pi device's saved installation Wi-Fi networks
from the Dashboard's **Device tab**, alongside the audio configuration
introduced by thread 33.

Bob, 2026-07-23: set network credentials from the Device tab in the same manner
as audio configuration, with support for storing multiple SSIDs and
passphrases.

## Bob gate

Design and Bob ratification come before implementation. This is a
facilitator-facing surface, writes privileged persistent system configuration,
handles secrets, and can disconnect the device being changed.

Design first (`1-network-config-design`), Bob ratifies, then build
(`2-network-config-implementation`).

## Scope and constraints

- Store an ordered collection of saved Wi-Fi profiles, each containing an SSID
  and its passphrase. Define add, update, remove, reorder/priority, and active
  network behavior.
- Decide whether open/hidden networks, Wi-Fi country, Ethernet, and static
  addressing belong in this first slice.
- Never report or echo stored passphrases through OSC status, WebSocket state,
  logs, command output, browser persistence, simulator fixtures, or repository
  files. The UI may report profile identity and whether a secret is configured.
- Follow the provision/convergence split: routine application is
  non-interactive; root operations use a narrow provisioned helper.
- Define staged validation, safe apply, reconnect, rollback or recovery, and
  operator feedback before implementation. Changing profile priority or
  deleting the active profile can remove the current control path.
- Do not assume an interface name or that every device has Wi-Fi, consistent
  with `docs/OSC-CONTRACT.md`.
- Coordinate the Device-tab placement with `33-device-audio-config`, while
  keeping network secrets out of `bopos.config` unless the ratified design
  proves that storage safe.
