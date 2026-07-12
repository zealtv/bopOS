#!/bin/bash
# Check out a git branch of bopOS. Called by bopos.py's /checkout handler,
# which then runs update.sh to pull + reboot. Usage: checkout.sh <branch>

BRANCH="$1"
if [ -z "$BRANCH" ]; then
  echo "Usage: checkout.sh <branch>"
  exit 1
fi

GITREPO_ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
cd "$GITREPO_ROOT" || exit 2

echo "--- clearing local changes"
git restore .
echo "--- fetching"
git fetch origin
echo "--- checking out $BRANCH"
git checkout "$BRANCH"
echo "--- updating submodules"
git submodule update --init --recursive
