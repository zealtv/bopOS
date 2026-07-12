#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"
mkdir -p "$RUN_DIR"

SOUNDCARD="${SOUNDCARD:-DigiAMP}"

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

# bopOS-owned run context, delivered atomically at launch (never over OSC)
eval "$(python3 "$BOPOS_DIR/python/runcontext.py" "$ACTIVE_PATCH")"
BOPOS_SEED="${BOPOS_SEED:-$((RANDOM % 1000000))}"
BOPOS_RUN_ID="${BOPOS_RUN_ID:-fallback-$BOPOS_SEED}"

echo "SEED: $BOPOS_SEED"
echo "RUN ID: $BOPOS_RUN_ID"

# Print the current active patch clearly
echo "====================="
echo "ACTIVE PATCH: $ACTIVE_PATCH"
echo "PATCH PATH: $PATCH_PATH"
echo "ENGINE: $ENGINE"
echo "PATCH ENTRYPOINT: $PATCH_PATH/$ENTRYPOINT"
echo "====================="

# Keep the legacy PD sample path attached to the framework asset slot.
ASSETS_DIR="$BOPOS_DIR/assets"
SAMPLEPACKS_DIR="$PATCH_PATH/bop/samplepacks"
SAMPLEPACKS_SLOT="$ASSETS_DIR/samplepacks"
mkdir -p "$SAMPLEPACKS_SLOT"
if [ -L "$SAMPLEPACKS_DIR" ] && [ "$(readlink -f "$SAMPLEPACKS_DIR")" = "$SAMPLEPACKS_SLOT" ]; then
    :
elif [ -d "$SAMPLEPACKS_DIR" ] && [ -z "$(find "$SAMPLEPACKS_SLOT" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    find "$SAMPLEPACKS_DIR" -mindepth 1 -maxdepth 1 -exec mv -t "$SAMPLEPACKS_SLOT" -- {} +
    rmdir "$SAMPLEPACKS_DIR"
    ln -s "$SAMPLEPACKS_SLOT" "$SAMPLEPACKS_DIR"
elif [ -d "$SAMPLEPACKS_DIR" ] && [ -n "$(find "$SAMPLEPACKS_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    echo "WARNING: BOTH LEGACY AND ASSET SAMPLEPACK DIRECTORIES HAVE CONTENT; LEAVING LEGACY DIRECTORY ALONE" >&2
elif [ -d "$SAMPLEPACKS_DIR" ]; then
    rmdir "$SAMPLEPACKS_DIR"
    ln -s "$SAMPLEPACKS_SLOT" "$SAMPLEPACKS_DIR"
elif [ ! -e "$SAMPLEPACKS_DIR" ] && [ ! -L "$SAMPLEPACKS_DIR" ]; then
    mkdir -p "$(dirname "$SAMPLEPACKS_DIR")"
    ln -s "$SAMPLEPACKS_SLOT" "$SAMPLEPACKS_DIR"
else
    echo "WARNING: LEGACY SAMPLEPACK PATH CANNOT BE ADOPTED: $SAMPLEPACKS_DIR" >&2
fi

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

export BOPOS_ASSETS="$BOPOS_DIR/assets"
if [ "$ENGINE" = "pd" ]; then
    echo "------------------- Starting Pure Data..."
    # PUREDATA — run context lands on the bopos-context bus in the same launch
    pd -nogui -jack -open "$PATCH_PATH/$ENTRYPOINT" -send "; bopos-context seed $BOPOS_SEED; bopos-context run-id $BOPOS_RUN_ID; bopos-context patch $ACTIVE_PATCH; bopos-context assets $BOPOS_DIR/assets" &
    ENGINE_PID=$!
    echo $ENGINE_PID > "$RUN_DIR/pd.pid"
else
    echo "------------------- Starting $ENGINE..."
    BOPOS_ACTIVEPATCH=$ACTIVE_PATCH BOPOS_SEED=$BOPOS_SEED BOPOS_RUN_ID=$BOPOS_RUN_ID BOPOS_ENGINE_PORT="${BOPOS_ENGINE_PORT:-6661}" "$ENGINE" "$PATCH_PATH/$ENTRYPOINT" &
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
