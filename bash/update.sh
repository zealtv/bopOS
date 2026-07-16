#!/bin/bash
# Converge the framework checkout without performing privileged provisioning or
# rebooting. python/bopos.py sends the terminal receipt and requests the reboot.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
SUDO="${BOPOS_SUDO:-/usr/bin/sudo}"
SYSTEMCTL="${BOPOS_SYSTEMCTL:-/usr/bin/systemctl}"
ACTIVE_PATCH_FILE="$BOPOS_DIR/patches/active_patch.txt"
ACTIVE_PATCH=""
ACTIVE_PATCH_SAVED=0
PHASE="authorization"

result() {
    printf 'BOPOS_UPDATE_RESULT status=%s phase=%s\n' "$1" "$2"
}

restore_active_patch() {
    if [ "$ACTIVE_PATCH_SAVED" -eq 1 ]; then
        printf '%s\n' "$ACTIVE_PATCH" > "$ACTIVE_PATCH_FILE"
    fi
}

failed() {
    status=$?
    trap - ERR
    restore_active_patch
    result err "$PHASE"
    exit "$status"
}
trap failed ERR

# Fail before touching the checkout if the background helper cannot perform the
# eventual reboot. -n is deliberately mandatory: runtime updates never prompt.
"$SUDO" -n -l "$SYSTEMCTL" reboot >/dev/null

PHASE="active-patch"
ACTIVE_PATCH="$(cat "$ACTIVE_PATCH_FILE")"
ACTIVE_PATCH_SAVED=1

cd "$BOPOS_DIR"
export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes}"

PHASE="restore"
echo "--- clearing tracked framework changes"
git restore .

PHASE="pull"
echo "--- pulling framework without interactive credentials"
git -c credential.interactive=never pull --ff-only --recurse-submodules

PHASE="active-patch"
echo "--- restoring active patch selection: $ACTIVE_PATCH"
restore_active_patch

PHASE="submodules"
echo "--- synchronizing framework submodules"
git submodule sync --recursive
git -c credential.interactive=never submodule update --init --recursive

trap - ERR
restore_active_patch
result ok converged
