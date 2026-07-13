#!/bin/bash
# Clear the framework-owned samplepacks asset slot. The one-release legacy
# patch path is a symlink to this directory; acquisition no longer lives here.

GITREPO_ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SAMPLES_DIR_PATH="$GITREPO_ROOT/assets/samplepacks"

echo "Clearing all contents from: $SAMPLES_DIR_PATH"

# Remove all contents of the directory, but not the directory itself
rm -rf "$SAMPLES_DIR_PATH"/*

# Re-create the directory if it was deleted (in case it was empty to start with)
mkdir -p "$SAMPLES_DIR_PATH"

echo "Samplepacks cleared successfully!"
