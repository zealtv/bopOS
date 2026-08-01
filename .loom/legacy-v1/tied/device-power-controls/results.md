# Results

Restored authenticated `/os/reboot` and `/os/shutdown` while keeping the bopOS
framework helper unprivileged.

## Root cause

The helper moved from a root launch context to user `pi`, but the callbacks
continued to call `systemctl reboot` and `systemctl poweroff` directly. The
background rc.local session cannot receive an interactive polkit challenge.
bop000 recorded `Call to Reboot failed: Interactive authentication required.`

## Changes

- Added a sudoers rule granting `pi` only the exact commands
  `/usr/bin/systemctl reboot` and `/usr/bin/systemctl poweroff`.
- Callbacks use absolute paths and non-interactive `sudo -n`, returning failure
  honestly if node provisioning is incomplete.
- Added a validating, idempotent installer. An unprivileged later update reuses
  already-working authorization without attempting another privileged write.
- Fresh Raspberry Pi provisioning installs the rule automatically through the
  documented `sudo bash/update.sh` path.
- Updated the fresh-node README description.

## Verification

Local:

- `verify_power_controls.py`: 9/9 passed.
- Python compilation, Bash syntax checks, and `git diff --check`: passed.

Hardware, bop000:

- Source policy parsed successfully with `visudo` before installation.
- Bob ran the one-time authenticated migration installer.
- Installed `/etc/sudoers.d/bopos-power` is `root:root`, mode `0440`.
- Full `/etc/sudoers` validation passed.
- `sudo -n -l` accepted both exact commands without a password.
- Direct authorized reboot completed successfully.
- After loading revision `07da6b1`, a targeted `/0/os/reboot` OSC message hit
  the real helper callback and rebooted the device end to end. bop000 returned
  at boot time `2026-07-14 14:42:31` with helper PID 1043, JACK PID 1068, PD
  PID 1082, active `bonks-pd`, and both PD outputs connected to hardware.
- Shutdown was not executed because bop000 cannot be powered back on remotely;
  its exact authorization and shared callback path were verified
  non-destructively.
