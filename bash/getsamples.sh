#!/bin/bash

# Resolve the active patch and source its config
GITREPO_ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
ACTIVE_PATCH_FILE="$GITREPO_ROOT/patches/active_patch.txt"

if [ ! -f "$ACTIVE_PATCH_FILE" ]; then
  echo "Error: active_patch.txt not found at $ACTIVE_PATCH_FILE"
  exit 1
fi

PATCH_NAME=$(cat "$ACTIVE_PATCH_FILE" | tr -d '\n')
PATCH_CONFIG="$GITREPO_ROOT/patches/$PATCH_NAME/bopos.config"

if [ ! -f "$PATCH_CONFIG" ]; then
  echo "Error: bopos.config not found for patch '$PATCH_NAME' at $PATCH_CONFIG"
  exit 1
fi

source "$PATCH_CONFIG"

# Define the hardcoded path for the sample packs destination directory
SAMPLES_DIR_PATH="$GITREPO_ROOT/patches/$PATCH_NAME/bop/samplepacks"

# Define a temporary file for the downloaded zip
TEMP_ZIP_FILE=$(mktemp)

echo "Downloading sample packs from $SAMPLEPACKSURL..."
# Download the zip file using gdown
/home/pi/venv/bin/gdown --fuzzy "$SAMPLEPACKSURL" -O "$TEMP_ZIP_FILE"

# Check if the download was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to download sample packs."
    rm "$TEMP_ZIP_FILE"
    exit 1
fi

echo "Extracting sample packs to $SAMPLES_DIR_PATH..."
# Unzip the downloaded file directly into the destination directory.
unzip -o "$TEMP_ZIP_FILE" -d "$SAMPLES_DIR_PATH"

# Check if the unzip was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to extract sample packs."
    rm "$TEMP_ZIP_FILE"
    exit 1
fi

# # --- CORRECTED CODE: Move contents up and delete the old folder ---
# # Get the name of the nested folder created by the unzip command.
# INNER_FOLDER_NAME=$(ls -1 "$SAMPLES_DIR_PATH" | head -n 1)

# echo "Moving contents of nested folder '$INNER_FOLDER_NAME' up one level..."
# # Move all files and folders from the nested directory into the parent directory.
# mv -f "$SAMPLES_DIR_PATH/$INNER_FOLDER_NAME"/* "$SAMPLES_DIR_PATH"

# # Remove the now empty nested folder.
# echo "Removing empty nested folder: $SAMPLES_DIR_PATH/$INNER_FOLDER_NAME"
# rmdir "$SAMPLES_DIR_PATH/$INNER_FOLDER_NAME"

# # --- END OF CORRECTED CODE ---

# Clean up the temporary zip file
rm "$TEMP_ZIP_FILE"

echo "Sample packs updated successfully!"
exit 0
