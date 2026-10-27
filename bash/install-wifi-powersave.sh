#!/bin/bash
# Keep Wi-Fi power save off (79-wifi-power-save). Idempotent; invoked by
# provision.sh at install time (sudo). Bria Fox lost its link mid-session on
# 2026-10-23 with power save on and never rejoined.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
CONF_SOURCE="$BOPOS_DIR/systemd/bopos-wifi-powersave.conf"
CONF_TARGET="/etc/NetworkManager/conf.d/bopos-wifi-powersave.conf"
UNIT_SOURCE="$BOPOS_DIR/systemd/bopos-wifi-powersave.service"
UNIT_TARGET="/etc/systemd/system/bopos-wifi-powersave.service"

as_root() {
    if [ "${EUID:-$(id -u)}" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

# The drop-in is inert where NetworkManager is absent, so install it always:
# a later switch to NetworkManager then inherits the setting.
as_root install -d -o root -g root -m 0755 /etc/NetworkManager/conf.d
if ! cmp -s "$CONF_SOURCE" "$CONF_TARGET"; then
    as_root install -o root -g root -m 0644 "$CONF_SOURCE" "$CONF_TARGET"
    if systemctl is-active --quiet NetworkManager; then
        as_root systemctl reload NetworkManager || true
    fi
fi
if ! cmp -s "$UNIT_SOURCE" "$UNIT_TARGET"; then
    as_root install -o root -g root -m 0644 "$UNIT_SOURCE" "$UNIT_TARGET"
    as_root systemctl daemon-reload
fi
as_root systemctl enable bopos-wifi-powersave.service
# Apply now too, so an existing node needs no reboot. Absent iw or wlan0
# (a wired bench node) is not an error.
if command -v iw >/dev/null 2>&1 && [ -e /sys/class/net/wlan0 ]; then
    as_root iw dev wlan0 set power_save off || true
fi
echo "Wi-Fi power save: off (NetworkManager drop-in + boot unit)"
