# How NetworkManager handles Wi-Fi on bopOS nodes

When building or debugging anything that changes which networks a node joins (`33b` network config, link recovery, provisioning), work from what NetworkManager was seen to do on real Pis, not from what list order implies.

Observed on Pi OS Trixie (Bria Fox 2026-10-28; noor-dusk 2026-11-05, NM 1.52.1):

- **NetworkManager manages `wlan0`.** It is the backend for `systemd/bopos-set-wifi`.
- **Imager-provisioned networks appear as netplan-generated profiles** named `netplan-wlan0-<ssid>`. Adopt by SSID, never by profile name. `nmcli con modify` on one persists across reboot (NM writes back to `/etc/netplan/90-NM-<uuid>.yaml`).
- **Priority only governs the choice at (re)connect.** When its network drops, NM joins any autoconnect profile in range and stays there after the preferred one returns (noor-dusk sat on priority-0 `<workshop-ssid>` for 5+ min after priority-10 `<dev-ssid>` came back). A disabled-but-saved network must have autoconnect off, or it can capture devices. The dashboard's warnings and docs should say so.
- **With power save off, NM's own reconnect survived a 60 s AP restart** 11/11 times (6–21 s to rejoin). That covered one node, a strong signal and 60 s outages only. bopOS doesn't nudge the link.
- **Unconfirmed:** a wrong-passphrase spell may block autoconnect until a power cycle (no secret agent on a headless node). `33b-device-network-config/3-wrong-key-lockout` owns the repro.

Evidence: `lore:2026-11-05-ap-restart-soak-noor-dusk`, `79-wifi-power-save` (tied).

## Associations

- [[hardware-claims]]
- [[cross-repo]]
