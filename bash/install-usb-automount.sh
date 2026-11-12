#!/bin/bash
# Install the bopOS USB auto-mount udev rule + systemd template unit
# (thread 42-node-logging). Idempotent; invoked by provision.sh at install
# time (sudo). Runtime needs no privilege — the node discovers the mount by
# its stable path.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RULE_SOURCE="$BOPOS_DIR/systemd/99-bopos-usb.rules"
RULE_TARGET="/etc/udev/rules.d/99-bopos-usb.rules"
UNIT_SOURCE="$BOPOS_DIR/systemd/bopos-usb@.service"
UNIT_TARGET="/etc/systemd/system/bopos-usb@.service"
HELPER_SOURCE="$SCRIPT_DIR/bopos-usb-mount"
HELPER_TARGET="/usr/local/sbin/bopos-usb-mount"

as_root() {
    if [ "${EUID:-$(id -u)}" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

changed=0
# Reinstall on every provisioning pass, as with the hostname/Wi-Fi helpers:
# matching bytes alone do not prove root ownership or executable permissions.
as_root install -o root -g root -m 0755 "$HELPER_SOURCE" "$HELPER_TARGET"
if ! cmp -s "$RULE_SOURCE" "$RULE_TARGET"; then
    as_root install -o root -g root -m 0644 "$RULE_SOURCE" "$RULE_TARGET"
    changed=1
fi
if ! cmp -s "$UNIT_SOURCE" "$UNIT_TARGET"; then
    as_root install -o root -g root -m 0644 "$UNIT_SOURCE" "$UNIT_TARGET"
    changed=1
fi

if [ "$changed" -eq 1 ]; then
    as_root udevadm control --reload-rules
    as_root systemctl daemon-reload
    echo "Installed bopOS USB auto-mount (udev rule + mount unit)"
else
    echo "bopOS USB auto-mount already installed"
fi
