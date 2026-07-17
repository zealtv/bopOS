#!/bin/bash
# Pull the latest changes for the currently active patch repo. Does not
# reboot itself: pull_active_patch_callback (python/bopos.py) sends the
# /os/rev outcome receipt first, then requests the reboot, so an operator
# always sees success/failure before the box goes down (contract sec 7).

PATCHES_DIR="$(dirname "$(dirname "$(realpath "$0")")")/patches"
ACTIVE_PATCH_FILE="$PATCHES_DIR/active_patch.txt"

if [ ! -f "$ACTIVE_PATCH_FILE" ]; then
  echo "active_patch.txt not found!"
  exit 1
fi

PATCH_NAME=$(cat "$ACTIVE_PATCH_FILE" | tr -d '\n')
PATCH_DIR="$PATCHES_DIR/$PATCH_NAME"

if [ ! -d "$PATCH_DIR/.git" ]; then
  echo "No git repo found in $PATCH_DIR!"
  exit 2
fi

cd "$PATCH_DIR" || exit 3
echo "--- clearing changes"
git restore .
echo "Pulling latest changes for $PATCH_NAME..."
git pull --recurse-submodules
if [ $? -eq 0 ]; then
  echo "Successfully updated $PATCH_NAME."
  echo "--- setting permissions to allow PD write access"
  chown -R pi /home/pi/bopOS
else
  echo "Failed to update $PATCH_NAME."
  exit 4
fi