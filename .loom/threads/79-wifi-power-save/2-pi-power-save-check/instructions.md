# 2-pi-power-save-check

Hardware proof for `1-provision-power-save-off`. Needs Bob, or SSH access to
a node; Claude can't SSH in, because nodes take password authentication only.

1. On a node (Bria Fox first, since she's the 2026-10-23 incident node):
   update bopOS, then `sudo bash/provision.sh`.
2. Record which tool manages Wi-Fi: `systemctl is-active NetworkManager`,
   `nmcli -t -f DEVICE,STATE dev`, and whether `dhcpcd` is running. This
   also answers the open platform seam in `systemd/bopos-set-wifi` and `33b`.
3. `iw dev wlan0 get power_save` → expect `off`. Reboot, then check again.
   Toggle the connection (`nmcli con down/up …` or an access-point restart),
   then check again.
4. Soak for a few hours with heartbeats watched on the dashboard, ideally
   with an access-point restart mid-run. Record whether the node stays
   reachable or recovers unaided.

Record the device, OS image and bopOS revision (glean `hardware-claims`) in
`verification.md` here.
