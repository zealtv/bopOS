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

if [ ! -x "$VISUDO" ]; then
    echo "ERROR: visudo not found at $VISUDO" >&2
    exit 1
fi

"$VISUDO" -cf "$SOURCE"
as_root install -o root -g root -m 0440 "$SOURCE" "$TARGET"
as_root "$VISUDO" -cf /etc/sudoers
echo "Installed $TARGET"
