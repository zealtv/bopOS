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
LEGACY_RC_LOCAL="/etc/rc.local"
LEGACY_RC_LOCAL_BACKUP="/etc/rc.local.bopos-legacy"

install -o root -g root -m 0755 "$BOPOS_DIR/systemd/bopos-set-hostname" \
    /usr/local/sbin/bopos-set-hostname
install -o root -g root -m 0755 "$SCRIPT_DIR/bopos" /usr/local/bin/bopos
install -d -o root -g root -m 0755 /usr/local/lib/bopos
install -o root -g root -m 0644 "$BOPOS_DIR/python/wifi_config.py" /usr/local/lib/bopos/wifi_config.py
install -o root -g root -m 0755 "$BOPOS_DIR/systemd/bopos-set-wifi" /usr/local/sbin/bopos-set-wifi
"$SCRIPT_DIR/install-power-control.sh"
"$SCRIPT_DIR/install-usb-automount.sh"
"$SCRIPT_DIR/install-wifi-powersave.sh"
chown -R pi:pi "$BOPOS_DIR"
# The IO bridge reads USB keyboards and mice from /dev/input (84-key-input).
# Raspberry Pi OS normally puts its first user in input already; make sure.
usermod -aG input pi

if [ ! -e "$CONFIG_FILE" ]; then
    install -o pi -g pi -m 0644 "$CONFIG_DEFAULTS" "$CONFIG_FILE"
    echo "Installed device defaults at $CONFIG_FILE"
else
    echo "Preserved existing device configuration at $CONFIG_FILE"
fi

# Stop the previous owner before replacing its unit definition. On the first
# adoption the legacy ExecStop is gone; a reboot is required to retire its
# unmanaged children. No PID files from that installation are ever trusted.
systemctl stop bopos.target bopos.service || true
if [ -f /etc/systemd/system/bopos.service ]; then
    systemctl disable bopos.service
fi
rm -f "$BOPOS_DIR/run/"{bopos,io,jackd,pd,engine}.pid "$BOPOS_DIR/run/engine.name"
for unit in bopos.target bopos.service bopos-io.service bopos-engine.service; do
    install -o root -g root -m 0644 "$BOPOS_DIR/systemd/$unit" "/etc/systemd/system/$unit"
done

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
systemctl enable bopos.target
# Publish only after every privileged installation step succeeded.
install -d -o root -g root -m 0755 /etc/bopos
install -o root -g root -m 0644 "$BOPOS_DIR/systemd/provision-level" /etc/bopos/provision-level

echo "Installed bopOS services, bopos command, and provision level"
echo "Reboot after first adoption. Use bopos status, restart, update, and logs thereafter."
