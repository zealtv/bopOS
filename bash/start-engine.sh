#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"
mkdir -p "$RUN_DIR"

if [ -f "$BOPOS_DIR/bopos.config" ]; then
    # shellcheck disable=SC1091
    source "$BOPOS_DIR/bopos.config"
fi
SOUNDCARD="${SOUNDCARD:-DigiAMP}"
MIXER_CONTROL="${MIXER_CONTROL:-}"
JACK_SAMPLE_RATE="${JACK_SAMPLE_RATE:-44100}"
JACK_PERIOD_SIZE="${JACK_PERIOD_SIZE:-512}"
JACK_NPERIODS="${JACK_NPERIODS:-2}"
JACK_START_TIMEOUT="${BOPOS_JACK_START_TIMEOUT:-15}"
JACK_STOP_TIMEOUT="${BOPOS_STOP_TIMEOUT:-15}"
AUDIO_WAIT_TIMEOUT="${BOPOS_AUDIO_WAIT_TIMEOUT:-60}"

stop_failed_jack() {
    pid="$1"
    kill "$pid" 2>/dev/null || true
    elapsed=0
    while kill -0 "$pid" 2>/dev/null; do
        if [ "$elapsed" -ge "$JACK_STOP_TIMEOUT" ]; then
            echo "WARNING: Jack did not stop within ${JACK_STOP_TIMEOUT}s; killing it" >&2
            kill -KILL "$pid" 2>/dev/null || true
            break
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    wait "$pid" 2>/dev/null || true
    rm -f "$RUN_DIR/jackd.pid"
}

# Determine active patch
ACTIVE_PATCH=$(cat "$BOPOS_DIR/patches/active_patch.txt")
PATCH_PATH="$BOPOS_DIR/patches/$ACTIVE_PATCH"

if ! MANIFEST_OUTPUT=$(python3 "$BOPOS_DIR/python/manifest.py" "$PATCH_PATH"); then
    echo "ERROR: PATCH REQUIRES A VALID bopos.patch.json: $PATCH_PATH" >&2
    exit 1
fi
eval "$MANIFEST_OUTPUT"

# Assets are exposed only through the engine-neutral run context. Retire the
# former patch-local samplepacks compatibility symlink and remove its empty
# framework-created target before discovering the installed slot list. Never
# delete a real directory or any content.
ASSETS_DIR="$BOPOS_DIR/assets"
LEGACY_SAMPLEPACKS="$PATCH_PATH/bop/samplepacks"
if [ -L "$LEGACY_SAMPLEPACKS" ]; then
    rm "$LEGACY_SAMPLEPACKS"
fi
rmdir "$ASSETS_DIR/samplepacks" 2>/dev/null || true

# bopOS-owned run context, delivered atomically at launch (never over OSC)
eval "$(python3 "$BOPOS_DIR/python/runcontext.py" "$ACTIVE_PATCH")"
BOPOS_SEED="${BOPOS_SEED:-$((RANDOM % 1000000))}"
BOPOS_RUN_ID="${BOPOS_RUN_ID:-fallback-$BOPOS_SEED}"
BOPOS_VERSION="${BOPOS_VERSION:-unknown}"
BOPOS_PATCH_FINGERPRINT="${BOPOS_PATCH_FINGERPRINT:-unknown}"
BOPOS_GROUPS="${BOPOS_GROUPS:--1}"
BOPOS_ASSETS="${BOPOS_ASSETS:-[]}"
BOPOS_ASSETS_PD="${BOPOS_ASSETS_PD:-}"
export BOPOS_ASSETS

echo "SEED: $BOPOS_SEED"
echo "RUN ID: $BOPOS_RUN_ID"
echo "VERSION: $BOPOS_VERSION"
echo "PATCH FINGERPRINT: $BOPOS_PATCH_FINGERPRINT"
echo "GROUPS: $BOPOS_GROUPS"
echo "ASSET SLOTS: $BOPOS_ASSETS"

# Print the current active patch clearly
echo "====================="
echo "ACTIVE PATCH: $ACTIVE_PATCH"
echo "PATCH PATH: $PATCH_PATH"
echo "ENGINE: $ENGINE"
echo "PATCH ENTRYPOINT: $PATCH_PATH/$ENTRYPOINT"
echo "====================="

#Start Jack
echo "Waiting up to ${AUDIO_WAIT_TIMEOUT}s for ALSA card: $SOUNDCARD"
AUDIO_READY=0
for ((i=0; i<=AUDIO_WAIT_TIMEOUT; i++)); do
    if [ -r /proc/asound/cards ] && grep -F "$SOUNDCARD" /proc/asound/cards >/dev/null; then
        AUDIO_READY=1
        break
    fi
    [ "$i" -lt "$AUDIO_WAIT_TIMEOUT" ] || break
    sleep 1
done
if [ "$AUDIO_READY" -ne 1 ]; then
    echo "ERROR: ALSA card '$SOUNDCARD' was not ready within ${AUDIO_WAIT_TIMEOUT}s" >&2
    exit 1
fi

echo "------------------- Starting Jack..."
# bopOS owns the configured device for the lifetime of this headless process.
# JACK's desktop-oriented D-Bus reservation cannot start without a display and
# otherwise rejects an unclaimed ALSA device.
export JACK_NO_AUDIO_RESERVATION="${JACK_NO_AUDIO_RESERVATION:-1}"
jackd -P70 -p16 -t2000 -d alsa -dhw:"$SOUNDCARD" \
    -p "$JACK_PERIOD_SIZE" -n "$JACK_NPERIODS" -r "$JACK_SAMPLE_RATE" -s -P&
JACK_PID=$!
echo $JACK_PID > "$RUN_DIR/jackd.pid"
# jackd -P80 -t2000 -d alsa -dhw:$SOUNDCARD -p 1024 -n 2 -r 22050 -s -P& #22khz

# Wait for the server itself, not a fixed delay. JACK_NO_START_SERVER prevents
# the readiness probe from spawning a different default server.
echo "Waiting up to ${JACK_START_TIMEOUT}s for Jack readiness..."
JACK_READY=0
for ((i=0; i<=JACK_START_TIMEOUT; i++)); do
    if ! kill -0 "$JACK_PID" 2>/dev/null; then
        wait "$JACK_PID" 2>/dev/null || true
        rm -f "$RUN_DIR/jackd.pid"
        echo "ERROR: Jack exited before becoming ready" >&2
        exit 1
    fi
    if JACK_NO_START_SERVER=1 jack_lsp >/dev/null 2>&1; then
        JACK_READY=1
        break
    fi
    [ "$i" -lt "$JACK_START_TIMEOUT" ] || break
    sleep 1
done
if [ "$JACK_READY" -ne 1 ]; then
    echo "ERROR: Jack did not become ready within ${JACK_START_TIMEOUT}s" >&2
    stop_failed_jack "$JACK_PID"
    exit 1
fi
echo "Jack is ready."
python3 "$BOPOS_DIR/python/audio_config.py" record-active \
    "$RUN_DIR/audio-config.json" "$SOUNDCARD" "$MIXER_CONTROL" \
    "$JACK_SAMPLE_RATE" "$JACK_PERIOD_SIZE" "$JACK_NPERIODS"

if [ "$ENGINE" = "pd" ]; then
    echo "------------------- Starting Pure Data..."
    # PUREDATA — run context lands on the bopos-context bus in the same launch
    pd -nogui -jack -open "$PATCH_PATH/$ENTRYPOINT" -send "; bopos-context seed $BOPOS_SEED; bopos-context run-id $BOPOS_RUN_ID; bopos-context patch $ACTIVE_PATCH; bopos-context assets $BOPOS_ASSETS_PD; bopos-context version $BOPOS_VERSION; bopos-context patch-fingerprint $BOPOS_PATCH_FINGERPRINT; bopos-context groups $BOPOS_GROUPS" &
    ENGINE_PID=$!
    echo $ENGINE_PID > "$RUN_DIR/pd.pid"
else
    echo "------------------- Starting $ENGINE..."
    BOPOS_ACTIVEPATCH=$ACTIVE_PATCH BOPOS_SEED=$BOPOS_SEED BOPOS_RUN_ID=$BOPOS_RUN_ID BOPOS_VERSION=$BOPOS_VERSION BOPOS_PATCH_FINGERPRINT=$BOPOS_PATCH_FINGERPRINT BOPOS_GROUPS="$BOPOS_GROUPS" BOPOS_ENGINE_PORT="${BOPOS_ENGINE_PORT:-6661}" "$ENGINE" "$PATCH_PATH/$ENTRYPOINT" &
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
