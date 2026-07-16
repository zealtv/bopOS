#!/bin/bash
# Select a bopOS branch without rebooting. update.sh performs the subsequent
# pull/convergence and python/bopos.py owns the receipt + reboot boundary.
set -Eeuo pipefail

BRANCH="${1:-}"
if [ -z "$BRANCH" ]; then
    echo "Usage: checkout.sh <branch>" >&2
    exit 2
fi
if ! git check-ref-format --branch "$BRANCH" >/dev/null 2>&1; then
    echo "Invalid branch name" >&2
    exit 2
fi

BOPOS_DIR="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
ACTIVE_PATCH_FILE="$BOPOS_DIR/patches/active_patch.txt"
ACTIVE_PATCH="$(cat "$ACTIVE_PATCH_FILE")"
PHASE="restore"

result() {
    printf 'BOPOS_CHECKOUT_RESULT status=%s phase=%s\n' "$1" "$2"
}

restore_active_patch() {
    printf '%s\n' "$ACTIVE_PATCH" > "$ACTIVE_PATCH_FILE"
}

failed() {
    status=$?
    trap - ERR
    restore_active_patch
    result err "$PHASE"
    exit "$status"
}
trap failed ERR

cd "$BOPOS_DIR"
export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never
GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh}"
if [[ "$GIT_SSH_COMMAND" != *BatchMode* ]]; then
    GIT_SSH_COMMAND+=" -o BatchMode=yes"
fi
export GIT_SSH_COMMAND

echo "--- clearing tracked framework changes"
git restore .

PHASE="fetch"
echo "--- fetching branches without interactive credentials"
REMOTE_REF="refs/remotes/origin/$BRANCH"
git -c credential.interactive=never fetch origin \
    "+refs/heads/$BRANCH:$REMOTE_REF"

PHASE="branch"
git show-ref --verify --quiet "$REMOTE_REF"

PHASE="checkout"
echo "--- checking out $BRANCH"
git checkout -B "$BRANCH" "$REMOTE_REF"
git branch --set-upstream-to="origin/$BRANCH" "$BRANCH"

trap - ERR
restore_active_patch
result ok checked-out
