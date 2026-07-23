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
CONFIG_FILE="$BOPOS_DIR/bopos.config"
CONFIG_DEFAULTS="$BOPOS_DIR/bopos.config.example"
SERVICE_SOURCE="$BOPOS_DIR/systemd/bopos.service"
SERVICE_TARGET="/etc/systemd/system/bopos.service"
LEGACY_RC_LOCAL="/etc/rc.local"
LEGACY_RC_LOCAL_BACKUP="/etc/rc.local.bopos-legacy"

install -o root -g root -m 0755 "$BOPOS_DIR/systemd/bopos-set-hostname" \
    /usr/local/sbin/bopos-set-hostname
"$SCRIPT_DIR/install-power-control.sh"
chown -R pi:pi "$BOPOS_DIR"

if [ ! -e "$CONFIG_FILE" ]; then
    install -o pi -g pi -m 0644 "$CONFIG_DEFAULTS" "$CONFIG_FILE"
    echo "Installed device defaults at $CONFIG_FILE"
else
    echo "Preserved existing device configuration at $CONFIG_FILE"
fi

install -o root -g root -m 0644 "$SERVICE_SOURCE" "$SERVICE_TARGET"

# Provisioning releases before systemd used this exact repository-owned
# rc.local. Back it up and retire it so bopOS cannot start twice. Never alter a
# site-owned rc.local that differs from the known legacy file.
if [ -f "$LEGACY_RC_LOCAL" ] && cmp -s "$LEGACY_RC_LOCAL" "$SCRIPT_DIR/rc.local"; then
    if [ ! -e "$LEGACY_RC_LOCAL_BACKUP" ]; then
        install -o root -g root -m 0755 "$LEGACY_RC_LOCAL" "$LEGACY_RC_LOCAL_BACKUP"
    fi
    rm "$LEGACY_RC_LOCAL"
    echo "Retired the legacy bopOS rc.local (backup: $LEGACY_RC_LOCAL_BACKUP)"
fi

systemctl daemon-reload
systemctl enable bopos.service

echo "Installed bopOS systemd service and privileged control authorization"
echo "Run bash/update.sh as pi to verify convergence, then reboot when ready"
