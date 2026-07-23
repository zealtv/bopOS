#!/bin/bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"
mkdir -p "$RUN_DIR"
# Active audio is a boot-local observation, not a claim carried across boots.
rm -f "$RUN_DIR/audio-config.json"

if [ -f "$BOPOS_DIR/bopos.config" ]; then
    # Node-local shell assignments; this file is owned and edited by the pi user.
    # shellcheck disable=SC1091
    source "$BOPOS_DIR/bopos.config"
fi
SOUNDCARD="${SOUNDCARD:-DigiAMP}"

start_failed() {
    status=$?
    trap - ERR
    echo "ERROR: bopOS startup failed; stopping the partial stack" >&2
    "$SCRIPT_DIR/stop.sh"
    exit "$status"
}
trap start_failed ERR

PRIMARY_INTERFACE=$(ip route get 1.1.1.1 2>/dev/null |
    awk '{for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}' || true)
if [ -z "$PRIMARY_INTERFACE" ]; then
    for interface in /sys/class/net/*; do
        [ "$(basename "$interface")" = "lo" ] && continue
        [ "$(cat "$interface/operstate" 2>/dev/null)" = "up" ] && PRIMARY_INTERFACE=$(basename "$interface") && break
    done
fi
if [ -z "$PRIMARY_INTERFACE" ]; then
    for interface in /sys/class/net/*; do
        [ "$(basename "$interface")" = "lo" ] && continue
        PRIMARY_INTERFACE=$(basename "$interface")
        break
    done
fi
MACADDRESS=$(cat "/sys/class/net/$PRIMARY_INTERFACE/address" 2>/dev/null || echo unknown)

if [ -x "$HOME/venv/bin/python" ]; then
    PYTHON_BIN="$HOME/venv/bin/python"
else
    PYTHON_BIN="python3"
fi


echo "------------------- Starting bopOS..."
echo "SOUNDCARD: $SOUNDCARD"
echo "MAC ADDRESS: $MACADDRESS"

# Start bopos.py to manage system functions
# NB: no sudo — start.sh runs as user `pi` (rc.local: `su pi -c`), and the `pi`
# user is in the i2c/gpio/audio groups, so these need no root. On images without
# passwordless sudo (e.g. Pi OS Trixie) a `sudo` here silently fails at boot.
echo "------------------- Starting bopos.py..."
"$PYTHON_BIN" "$BOPOS_DIR/python/bopos.py" "$MACADDRESS" &
echo $! > "$RUN_DIR/bopos.pid"

# Start io/main.py to access sensors and peripherals
echo "------------------- Starting io/main.py..."
( cd "$BOPOS_DIR/python/io" && exec "$PYTHON_BIN" "$BOPOS_DIR/python/io/main.py" ) &
echo $! > "$RUN_DIR/io.pid"

sleep 1



SOUNDCARD="$SOUNDCARD" "$SCRIPT_DIR/start-engine.sh"

trap - ERR
