#!/bin/bash
# First-time privileged Pi setup. Routine /os/updatebopos convergence must not
# call this script: it is intentionally allowed to install root-owned files.
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "ERROR: provision.sh must run as root (sudo bash/provision.sh)" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"

"$SCRIPT_DIR/install-power-control.sh"
chown -R pi:pi "$BOPOS_DIR"
install -o root -g root -m 0755 "$SCRIPT_DIR/rc.local" /etc/rc.local
echo "Installed bopOS boot entry and power authorization"
echo "Run bash/update.sh as pi to verify convergence, then reboot when ready"
