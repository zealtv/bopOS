# bop000 engine-only patch switch — live result

Date: 2026-07-14 AEST

## Deployment

- Pushed `origin/main` from `ec33524` to `9a660ae` (19 commits).
- bop000 fast-forwarded successfully and preserved `bonks-pd` as its active
  patch.
- `bash/update.sh` could not copy `rc.local` or call `systemctl reboot` because
  passwordless sudo/polkit is not configured. The existing `/etc/rc.local` was
  already correct and enabled-runtime; Bob rebooted the Pi manually.
- After reboot, the framework started normally from `/etc/rc.local` at revision
  `9a660ae`.

## Live switch

Bob selected `demo-pd` from the bop000 dashboard patch dropdown.

Observed once per second over SSH:

- helper stayed PID **1078** for the entire operation;
- active patch changed `bonks-pd` → `demo-pd`;
- old JACK/PD PIDs **1096/1115** stopped;
- replacement JACK/PD PIDs **1326/1388** started;
- PD downtime was approximately six seconds, dominated by the launcher's
  intentional JACK wait;
- bop000 never rebooted or dropped SSH;
- ports 6660 (helper), 6661 (PD), and 7770 (helper) were present afterward;
- replacement PD received `patch demo-pd`, a fresh seed, and run ID
  `demo-pd-20260714-141153-749269` in its launch context.

Bob confirmed the dashboard changed to `demo-pd` and refreshed its parameter
controls. Audio was already present before the switch and the replacement PD
process remained healthy after it.

## Follow-up

Patch switching is hardware-proven. The separate `restart-engine` action remains
opaque in the current interface, and the updater's sudo assumptions need a later
operational cleanup. Bob's next requested design pass is to assume one selected
patch fleet-wide and simplify the patch/interface model around that constraint.
