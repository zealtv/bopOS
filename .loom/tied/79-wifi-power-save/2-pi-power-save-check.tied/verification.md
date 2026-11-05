# Verification (Bob on Bria Fox, 2026-10-28)

**Device:** Bria Fox, Pi 3 Model A+, DigiAMP+, Pi OS Trixie 64-bit (the
hardware and OS as recorded on 2026-10-23; not re-checked today). bopOS
was at or after `6ceaf19`, because `provision.sh` ran the power-save
installer. The exact revision wasn't captured.

1. `sudo ./bash/provision.sh` printed `Wi-Fi power save: off (NetworkManager
   drop-in + boot unit)`, and right afterwards `iw dev wlan0 get power_save`
   gave `Power save: off`. `systemctl enable` warned "Unit
   …bopos-wifi-powersave.service is added as a dependency to a non-existent
   unit sys-subsystem-net-devices-wlan0.device". That's systemd's usual
   message when the target is a runtime device unit with no unit file. The
   link was created, and after the reboot the device unit was plugged and
   the service had run (below), so the warning is harmless.
2. **Network manager: NetworkManager.** `systemctl is-active NetworkManager`
   gave `active`; `nmcli -t -f DEVICE,STATE dev` gave `wlan0:connected`. This
   answers the open platform question for `systemd/bopos-set-wifi` and
   `33b/2` slice 0.
3. **After the reboot:**
   - `sys-subsystem-net-devices-wlan0.device`: active (plugged) since
     11:13:57;
   - `bopos-wifi-powersave.service`: enabled, active (exited), status
     0/SUCCESS at 11:14:01;
   - `iw dev wlan0 get power_save`: `Power save: off`.

**Not run:** the connection toggle (`nmcli con down/up`) from step 3. Proof
that power save stays off across a reconnect therefore rests on the soak
with an access-point restart, which is hardware check 13 in `76-bob-review`.
