#!/bin/bash
# Human update: execute as pi; only provisioning and target control use sudo.
set -euo pipefail
# Parse the whole function before git replaces this script on disk.
update_node() {
    root="$(cd "$(dirname "$0")/.." && pwd)"
    cd "$root"
    active=$(cat patches/active_patch.txt)
    before=$(git rev-parse HEAD)
    # The tracked selector is local state; always put it back, even on failure.
    restore_patch() { printf '%s\n' "$active" > patches/active_patch.txt; }
    trap restore_patch EXIT
    git restore -- patches/active_patch.txt
    git -c credential.interactive=never pull --ff-only --recurse-submodules
    git submodule sync --recursive
    git -c credential.interactive=never submodule update --init --recursive
    restore_patch
    after=$(git rev-parse HEAD)
    installed=$(cat /etc/bopos/provision-level 2>/dev/null || echo 0)
    required=$(cat systemd/provision-level)
    [[ "$installed" =~ ^[0-9]+$ ]] || installed=0
    [[ "$required" =~ ^[0-9]+$ ]] || { echo 'Invalid framework provision level' >&2; return 1; }
    changed=$(git diff --name-only "$before" "$after" -- systemd bash/provision.sh \
        bash/install-power-control.sh bash/install-usb-automount.sh \
        bash/install-wifi-powersave.sh bash/bopos python/wifi_config.py)
    if [ "$installed" -lt "$required" ] || [ -n "$changed" ]; then
        sudo "$root/bash/provision.sh"
    fi
    # Restore before restart can terminate this process's calling session.
    trap - EXIT
    sudo /usr/bin/systemctl restart bopos.target
}
update_node
