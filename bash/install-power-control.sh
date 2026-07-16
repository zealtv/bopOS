#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
SOURCE="$BOPOS_DIR/systemd/bopos-power.sudoers"
TARGET="/etc/sudoers.d/bopos-power"
VISUDO="/usr/sbin/visudo"

as_root() {
    if [ "${EUID:-$(id -u)}" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

# Framework updates run as the unprivileged helper after initial provisioning.
# If both exact commands are already authorized, no privileged rewrite is
# necessary (and sudo must not try to prompt on the helper's background tty).
if [ "${EUID:-$(id -u)}" -ne 0 ] \
        && sudo -n -l /usr/bin/systemctl reboot >/dev/null 2>&1 \
        && sudo -n -l /usr/bin/systemctl poweroff >/dev/null 2>&1 \
        && sudo -n -l /usr/local/sbin/bopos-set-hostname bopos-check >/dev/null 2>&1; then
    echo "bopOS privileged control authorization is already installed"
    exit 0
fi

if [ ! -x "$VISUDO" ]; then
    echo "ERROR: visudo not found at $VISUDO" >&2
    exit 1
fi

"$VISUDO" -cf "$SOURCE"
as_root install -o root -g root -m 0440 "$SOURCE" "$TARGET"
as_root "$VISUDO" -cf /etc/sudoers
echo "Installed $TARGET"
