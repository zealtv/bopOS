#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"
mkdir -p "$RUN_DIR"

SOUNDCARD="${SOUNDCARD:-DigiAMP}"
RND=$RANDOM
now=$(date --iso-8601=seconds)
STARTDATE=$(date -d "$now" +%Y%m%d)
STARTTIME=$(date -d "$now" +%H%M%S)

# Determine active patch
ACTIVE_PATCH=$(cat "$BOPOS_DIR/patches/active_patch.txt")
PATCH_PATH="$BOPOS_DIR/patches/$ACTIVE_PATCH"

MANIFEST_OUTPUT=$(python3 "$BOPOS_DIR/python/manifest.py" "$PATCH_PATH")
MANIFEST_STATUS=$?
eval "$MANIFEST_OUTPUT"
# even a failed python3 must not silence the node: fall back to legacy pd
ENGINE="${ENGINE:-pd}"
ENTRYPOINT="${ENTRYPOINT:-main.pd}"
if [ "$MANIFEST_STATUS" -eq 1 ]; then
    echo "WARNING: INVALID PATCH MANIFEST; USING LEGACY LAUNCH"
fi

echo "RANDOM: $RND"
echo "STARTDATE: $STARTDATE"
echo "STARTTIME: $STARTTIME"

# Print the current active patch clearly
echo "====================="
echo "ACTIVE PATCH: $ACTIVE_PATCH"
echo "PATCH PATH: $PATCH_PATH"
echo "ENGINE: $ENGINE"
echo "PATCH ENTRYPOINT: $PATCH_PATH/$ENTRYPOINT"
echo "====================="

#Start Jack
echo "------------------- Starting Jack..."
jackd -P70 -p16 -t2000 -d alsa -dhw:$SOUNDCARD -p 512 -n 2 -r 44100 -s -P& #44.1khz
echo $! > "$RUN_DIR/jackd.pid"
# jackd -P80 -t2000 -d alsa -dhw:$SOUNDCARD -p 1024 -n 2 -r 22050 -s -P& #22khz

# Wait up to 15 seconds for Jack, allow skip by key press
WAIT_TIME=5
SKIP=0
printf "Waiting %ds for Jack (press any key to skip)...\n" "$WAIT_TIME"
if [ -t 0 ]; then stty -echo -icanon time 0 min 0; fi
for ((i=0; i<$WAIT_TIME; i++)); do
    [ -t 0 ] && read -t 1 -n 1 key && SKIP=1 && break
    printf "."
    sleep 1
done
if [ -t 0 ]; then stty sane; fi
echo ""
if [ $SKIP -eq 1 ]; then
    echo "Wait for Jack skipped by key press."
else
    echo "Wait for Jack complete."
fi

if [ "$ENGINE" = "pd" ]; then
    echo "------------------- Starting Pure Data..."
    # PUREDATA
    pd -nogui -jack -open "$PATCH_PATH/$ENTRYPOINT" -send "; RANDOM $RND; STARTTIME $STARTTIME; STARTDATE $STARTDATE; ACTIVEPATCH $ACTIVE_PATCH" &
    ENGINE_PID=$!
    echo $ENGINE_PID > "$RUN_DIR/pd.pid"
else
    echo "------------------- Starting $ENGINE..."
    BOPOS_ACTIVEPATCH=$ACTIVE_PATCH BOPOS_RANDOM=$RND BOPOS_STARTDATE=$STARTDATE BOPOS_STARTTIME=$STARTTIME "$ENGINE" "$PATCH_PATH/$ENTRYPOINT" &
    ENGINE_PID=$!
fi
echo $ENGINE_PID > "$RUN_DIR/engine.pid"
basename "$ENGINE" > "$RUN_DIR/engine.name"

# run active patch start script if it exists
if [ -f "$PATCH_PATH/start.sh" ]; then
    echo "------------------- Running patch start script..."
    bash "$PATCH_PATH/start.sh"
else
    echo "------------------- No patch start script found, skipping..."
fi
