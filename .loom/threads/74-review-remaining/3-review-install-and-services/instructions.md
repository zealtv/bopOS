# 3-review-install-and-services

**Status:** ready
**Goal:** review how bopOS is installed and kept running on a Pi and on the
host.

Scope: `install-device.sh`, `install-dashboard.sh`, `run.sh`,
`bash/provision.sh`, `bash/start.sh` / `start-engine.sh` / `stop*.sh`,
`bash/install-power-control.sh`, `bash/install-usb-automount.sh`, the
`systemd/` units and sudoers files.

Look for: failure handling (the `start.sh` ERR trap is `58/4`'s problem — don't
duplicate), idempotency of re-running installers, privilege scope of each
sudoers rule (feeds `33b/0-lan-trust-review`), hard-coded paths and users,
and anything that only works on one Pi OS release. Shellcheck if available.
Hardware claims stay separate (`glean:hardware-claims`).
