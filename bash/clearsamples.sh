#!/bin/bash
# Clear the downloaded sample packs for the currently active patch.
# Mirrors getsamples.sh: samples live under the active patch's bop/samplepacks.

GITREPO_ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
ACTIVE_PATCH_FILE="$GITREPO_ROOT/patches/active_patch.txt"

if [ ! -f "$ACTIVE_PATCH_FILE" ]; then
  echo "Error: active_patch.txt not found at $ACTIVE_PATCH_FILE"
  exit 1
fi

PATCH_NAME=$(cat "$ACTIVE_PATCH_FILE" | tr -d '\n')
SAMPLES_DIR_PATH="$GITREPO_ROOT/patches/$PATCH_NAME/bop/samplepacks"

echo "Clearing all contents from: $SAMPLES_DIR_PATH"

# Remove all contents of the directory, but not the directory itself
rm -rf "$SAMPLES_DIR_PATH"/*

# Re-create the directory if it was deleted (in case it was empty to start with)
mkdir -p "$SAMPLES_DIR_PATH"

echo "Samplepacks cleared successfully!"
