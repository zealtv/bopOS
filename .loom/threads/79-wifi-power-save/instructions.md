# 79-wifi-power-save

**Status:** ready (added 2026-10-23 at Bob's request: *"we can't have that
happen during a live event"*)
**Goal:** a provisioned bopOS node keeps its Wi-Fi link through a show — Wi-Fi
power save is off on every node and stays off across reboots, and a node that
does lose its link recovers without a power cycle.

## Evidence (2026-10-23, Bria Fox)

Bria Fox: Pi 3 Model A+, Raspberry Pi DigiAMP+, Pi OS Trixie 64-bit, bopOS
`26acbd7`, freshly installed with `install-device.sh` the day before.

- `run/bopos.log.prev` shows heartbeats failing with `[Errno 101] Network is
  unreachable` every 2 s from 13:45:50 until Bob pulled power at 13:49:48
  (120 failures). The node software kept running; nothing else was logged
  just before. Pi clock has no RTC, so timestamps are approximate.
- The node never rejoined. After a power cycle it came back with a new DHCP
  lease (`.99`, was `.163`). Red power LED steady at the time of the hang;
  `vcgencmd get_throttled` = `0x0` after reboot.
- After reboot, `iw dev wlan0 get power_save` reported `Power save: on`.
  Nothing in bopOS (`install-device.sh`, `bash/provision.sh`, node code)
  touches Wi-Fi power save.
- Confounder: the dashboard Mac also lost its network around the same time
  (`Network is unreachable` and `Can't assign requested address` on
  broadcasts; its sender briefly rebound to a `192.168.50.x` source). So an
  access-point blip may have triggered the drop; the Mac recovered and the
  Pi did not. Whether the router restarted was not captured.
- Persistent journald is off, so the kernel/NetworkManager log of the failed
  boot is gone.

Power save on the onboard Broadcom Wi-Fi is a widely reported cause of Pi
links that drop and don't recover — general knowledge, not yet measured on
this rig. Prior art in lore: `2026-09-22-esp32-s3-node-feasibility` warns
that Wi-Fi power save "will eat your events" for the broadcast contract.

## Next actions

1. Confirm what manages Wi-Fi on current Pi OS (NetworkManager on Trixie is
   expected — inspect, don't assume; `33b` noted the network manager still
   needs inspecting on a real Pi).
2. Choose the persistent mechanism (e.g. a NetworkManager conf drop-in with
   `wifi.powersave = 2`, vs a udev/systemd `iw ... power_save off`). It is
   root-owned, so it belongs in `bash/provision.sh`, which `install-device.sh`
   runs; existing nodes need one manual `sudo bash/provision.sh`.
3. Consider surfacing the state in the node report (e.g. `wifi_power_save`)
   so the dashboard can flag a node that has it on.
4. Consider recovery as a separate stitch: the node logged 2 minutes of
   `unreachable` without trying anything. Whether bopOS should nudge the link
   (or leave it to the OS) is a design question — propose before building
   (see glean `decision-gates`).

## Done when

- On a real Pi, after a fresh install and after a reboot,
  `iw dev wlan0 get power_save` reports `off`; record device, OS image and
  bopOS revision (glean `hardware-claims`).
- `docs/INSTALL.md` says provisioning disables Wi-Fi power save and that older
  nodes need the one-off `sudo bash/provision.sh`.
- Software tests cover the provisioning change where the existing provision
  tests reach.
- A soak (a few hours, ideally with an access-point restart mid-run) shows the
  node stays reachable or recovers unaided. Until it runs, the hardware half
  stays an open claim.
