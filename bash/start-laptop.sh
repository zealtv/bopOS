#!/bin/bash

# start-laptop.sh — Run bopOS on a laptop with MCP2221A USB-to-I2C adapter
# Equivalent of start.sh but for macOS/Linux laptop development

# --- Configuration (edit these as needed) ---
PD_BIN="pd"              # Path to Pure Data binary. macOS example:
                          # "/Applications/Pd-0.55-0.app/Contents/Resources/bin/pd"
PYTHON_BIN="python3"     # Python with blinka/adafruit deps installed

# --- Auto-detect paths ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"
mkdir -p "$RUN_DIR"

# --- Environment for MCP2221A USB I2C ---
export BLINKA_MCP2221=1

# --- Active patch ---
ACTIVEPATCH=$(cat "$BOPOS_DIR/patches/active_patch.txt" | tr -d '[:space:]')
PATCH_PATH="$BOPOS_DIR/patches/$ACTIVEPATCH"
PATCH_ENTRYPOINT="$PATCH_PATH/main.pd"

# --- bopOS-owned run context, delivered atomically at launch ---
eval "$("$PYTHON_BIN" "$BOPOS_DIR/python/runcontext.py" "$ACTIVEPATCH")"
BOPOS_SEED="${BOPOS_SEED:-$((RANDOM % 1000000))}"
BOPOS_RUN_ID="${BOPOS_RUN_ID:-fallback-$BOPOS_SEED}"

echo "===================="
echo "bopOS laptop mode"
echo "===================="
echo "ACTIVE PATCH: $ACTIVEPATCH"
echo "PATCH PATH:   $PATCH_PATH"
echo "SEED:         $BOPOS_SEED"
echo "RUN ID:       $BOPOS_RUN_ID"
echo "===================="

# --- Start io/main.py ---
echo "--- Starting io/main.py..."
( cd "$BOPOS_DIR/python/io" && exec "$PYTHON_BIN" "$BOPOS_DIR/python/io/main.py" ) &
echo $! > "$RUN_DIR/io.pid"

sleep 1

# --- Start Pure Data (with GUI, no jack) ---
echo "--- Starting Pure Data..."
$PD_BIN -path "$BOPOS_DIR/pd" -open "$PATCH_ENTRYPOINT" \
  -send "; bopos-context seed $BOPOS_SEED; bopos-context run-id $BOPOS_RUN_ID; bopos-context patch $ACTIVEPATCH; bopos-context assets $BOPOS_DIR/assets" &
echo $! > "$RUN_DIR/pd.pid"

# --- Run patch start script if exists ---
if [ -f "$PATCH_PATH/start.sh" ]; then
    echo "--- Running patch start script..."
    bash "$PATCH_PATH/start.sh"
else
    echo "--- No patch start script found, skipping..."
fi
