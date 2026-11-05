# AP-restart soak on noor-dusk: 11/11 unaided rejoins with power save off; NetworkManager platform facts (2026-11-05)

Results handed over from the kite-choir-brains session of 2026-11-05 (Bob + Claude): a bench soak in which a mANTBox's radio was disabled for 60 s eleven times while noor-dusk (Pi 3 A+, Trixie, NetworkManager 1.52.1, bopOS `74a9717`, power save `off` before and after) sat on it. Every bounce rejoined unaided, 6–21 s after the AP returned. Also two NetworkManager facts for `33b` (netplan-generated profile names; NM falls back to any autoconnect profile in range and doesn't return to a higher-priority one) and an unconfirmed wrong-key lockout that only a power cycle cleared.

## Source

`.nest/in/2026-11-05-ap-restart-soak-noor-dusk/` as dropped by that session, kept whole:
`content/request.md` and the raw logs in `content/attachments/` (node-side SSID/signal/gateway
poll every 2 s, 15:38–16:35; Mac-side ping state changes). The complete write-up lives in
kite-choir-brains as `lore:2026-11-05-ap-restart-recovery-soak-noor-dusk` (brains commit
`1f5490a`); the wrong-key addendum is brains commit `6a3b932`.

Redacted before the first push (Bob, 2026-11-05): network names and the node's LAN address are
replaced with `<dev-ssid>`, `<workshop-ssid>` and `<node-ip>`. The unredacted originals stay in
kite-choir-brains.

Closes the hardware half of `79-wifi-power-save` (hardware check 13 in `76-bob-review`).
Guidance carried forward in glean `networkmanager-wifi`.

## Tags

- wifi
- networkmanager
- power-save
- soak
- noor-dusk
- kite-choir
