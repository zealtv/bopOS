#!/bin/bash

#1.) get list of available soundcards by running: cat /proc/asound/cards
#2.) edit the SOUNDCARD variable below as needed

#SOUNDCARD="YOUR_SOUNDCARD"
# SOUNDCARD="sndrpihifiberry"
# SOUNDCARD="IQaudIODAC"
SOUNDCARD="DigiAMP"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"
mkdir -p "$RUN_DIR"

PRIMARY_INTERFACE=$(ip route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}')
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


# sleep 15

echo "------------------- Waiting..."
# Wait up to 15 seconds, allow skip by key press
WAIT_TIME=15
SKIP=0
printf "Waiting %ds (press any key to skip)...\n" "$WAIT_TIME"
if [ -t 0 ]; then stty -echo -icanon time 0 min 0; fi
for ((i=0; i<$WAIT_TIME; i++)); do
    [ -t 0 ] && read -t 1 -n 1 key && SKIP=1 && break
    printf "."
    sleep 1
done
if [ -t 0 ]; then stty sane; fi
echo ""
if [ $SKIP -eq 1 ]; then
    echo "Wait skipped by key press."
else
    echo "Wait complete."
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

exit
