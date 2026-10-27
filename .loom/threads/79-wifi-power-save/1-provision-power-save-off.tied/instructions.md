# 1-provision-power-save-off

Software half of the thread (2026-10-27): provisioning turns Wi-Fi power save
off and keeps it off.

## Built

Which network manager current Pi OS uses on a real node is still
unconfirmed: `systemd/bopos-set-wifi` still marks it as a platform seam. So
the fix covers both cases and doesn't assume either:

- `systemd/bopos-wifi-powersave.conf` → `/etc/NetworkManager/conf.d/`:
  `[connection] wifi.powersave = 2`. NetworkManager reapplies it on every
  (re)connect, which a single `iw` call wouldn't survive. It has no effect
  where NetworkManager is absent.
- `systemd/bopos-wifi-powersave.service`: a oneshot bound to the wlan0
  device that runs `iw dev wlan0 set power_save off` and exits 0 when `iw`
  is missing. It covers a node whose Wi-Fi isn't managed by NetworkManager.
- `bash/install-wifi-powersave.sh`: an idempotent installer. It installs
  both, reloads NetworkManager if it's running, enables the unit, and
  applies `iw` immediately so an existing node needs no reboot. `provision.sh`
  calls it.
- `docs/INSTALL.md`: says provisioning turns power save off, and that
  existing nodes need one `sudo bash/provision.sh`, checked with
  `iw dev wlan0 get power_save`.
- `tests/test_wifi_powersave.py` (fast suite).

Not built: the stitch's optional `wifi_power_save` report field. It would
add a contract field and is easy to add once `2-` shows what real nodes
report.
