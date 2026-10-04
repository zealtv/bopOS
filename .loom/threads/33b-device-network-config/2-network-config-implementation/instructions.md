# 2-network-config-implementation

**Status:** waiting on `1-network-config-design` being ratified
**Goal:** build the ratified design.

Placeholder. Before claiming, replace with the checklist, affected files and
verification gates from `1`'s `decisions.md`.

## Carried from `0`'s ruling (2026-10-04)

- **Platform first:** with a device up, find which network manager the
  supported Pi OS images use (don't assume `wpa_supplicant` / NetworkManager /
  `wlan0`) and how a hidden SSID is marked so the device probes for it.
- **Docs:** note that the trust model is workshop provisioning plus network
  isolation (`../0-lan-trust-review/ruling.md`).
- **Real-Pi gate:** the workshop switchover rehearsal — both APs up, disable
  testing from the dash, every device reappears on the show network.
