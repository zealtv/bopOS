# Verification

## Software and reboot (2026-10-28)

`1-provision-power-save-off` and `2-pi-power-save-check` (Bria Fox): power
save `off` after `provision.sh` and after a reboot; `docs/INSTALL.md` §
provisioning covers it, including the one-off `sudo bash/provision.sh` for
older nodes.

## Soak with AP restarts (2026-11-05, kite-choir-brains session)

From `lore:2026-11-05-ap-restart-soak-noor-dusk`:

- **Rig:** noor-dusk, Pi 3 Model A Plus Rev 1.1, Debian 13 (trixie), kernel
  6.18.50+rpt-rpi-v8, NetworkManager 1.52.1, bopOS `74a9717`. AP: MikroTik
  mANTBox 2 12s, RouterOS 7.25.1, 2.4 GHz ch 6, about −45 dBm at the bench.
- **Stimulus:** the AP's radio disabled for 60 s, 11 times, 15:38–16:35
  (about an hour rather than the "few hours" this stitch asked for).
- **Result:** 11/11 rejoined unaided, 6–21 s after the AP returned; no hang,
  no power cycle; heartbeats back on the dashboard each time.
  `iw dev wlan0 get power_save` read `off` before and after the soak.
- **Limits:** one node, strong signal, 60 s outages only. No A/B with power
  save on: Bob declined it (2026-11-05), since power save is off on purpose.
  The 2026-10-23 Bria Fox hang had power save on.

Bob, 2026-11-05, in chat: *"i think we can close 79-wifi-powersave."*
