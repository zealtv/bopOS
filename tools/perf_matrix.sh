#!/bin/bash
# Tuning matrix: run the active patch under a grid of jackd settings and
# collect one perf_measure report per cell (see docs/PERF.md).
#
#   tools/perf_matrix.sh [-d seconds] [-s soundcard] [-o outdir] [-c "cells"]
#
# Cells are rate:period:nperiods triples. The default grid brackets the
# production start.sh line (44100:512:2) and includes the commented 22.05k
# fallback. Takes over the audio device: stops any running engine+jackd
# (bopos.py and the io bridge are left running, production-like), and leaves
# the stack stopped when done — restart with bash/start-engine.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"

DURATION=60
SOUNDCARD="${SOUNDCARD:-DigiAMP}"
OUTDIR="$BOPOS_DIR/run/perf-$(date +%Y%m%d-%H%M%S)"
CELLS="44100:512:2 44100:256:2 44100:1024:2 44100:512:3 22050:1024:2"

while getopts "d:s:o:c:h" opt; do
    case $opt in
        d) DURATION="$OPTARG" ;;
        s) SOUNDCARD="$OPTARG" ;;
        o) OUTDIR="$OPTARG" ;;
        c) CELLS="$OPTARG" ;;
        *) sed -n '2,11p' "$0"; exit 1 ;;
    esac
done

ACTIVE_PATCH=$(cat "$BOPOS_DIR/patches/active_patch.txt")
PATCH_PATH="$BOPOS_DIR/patches/$ACTIVE_PATCH"
ENTRYPOINT=main.pd
REPORT="$OUTDIR/report.jsonl"
mkdir -p "$OUTDIR"

echo "Matrix over: $CELLS"
echo "Patch: $ACTIVE_PATCH  soundcard: $SOUNDCARD  ${DURATION}s/cell"
echo "Reports: $REPORT"
echo "Stopping any running engine/jack (bopos.py stays up)..."
"$SCRIPT_DIR/../bash/stop-engine.sh"
sleep 2

cleanup() {
    pkill -x pd 2>/dev/null
    pkill -x jackd 2>/dev/null
}
trap cleanup EXIT INT TERM

for cell in $CELLS; do
    RATE="${cell%%:*}"; rest="${cell#*:}"
    PERIOD="${rest%%:*}"; NPERIODS="${rest#*:}"
    LABEL="r$RATE-p$PERIOD-n$NPERIODS"
    JACKLOG="$OUTDIR/jackd-$LABEL.log"
    echo ""
    echo "=== cell $LABEL ==="

    # Same flags as bash/start-engine.sh apart from the swept -r/-p/-n.
    jackd -P70 -p16 -t2000 -d alsa -dhw:"$SOUNDCARD" \
        -p "$PERIOD" -n "$NPERIODS" -r "$RATE" -s -P >"$JACKLOG" 2>&1 &
    JACK_PID=$!

    ok=0
    for _ in $(seq 1 20); do
        sleep 0.5
        jack_lsp >/dev/null 2>&1 && ok=1 && break
    done
    if [ "$ok" -ne 1 ]; then
        echo "jackd failed to come up for $LABEL (see $JACKLOG); skipping"
        kill "$JACK_PID" 2>/dev/null; wait "$JACK_PID" 2>/dev/null
        continue
    fi

    # PD launch mirrors bash/start-engine.sh (run context via bopos-context).
    eval "$(python3 "$BOPOS_DIR/python/runcontext.py" "$ACTIVE_PATCH")"
    BOPOS_SEED="${BOPOS_SEED:-$((RANDOM % 1000000))}"
    BOPOS_RUN_ID="${BOPOS_RUN_ID:-perf-$LABEL}"
    BOPOS_VERSION="${BOPOS_VERSION:-unknown}"
    BOPOS_PATCH_FINGERPRINT="${BOPOS_PATCH_FINGERPRINT:-unknown}"
    BOPOS_ASSETS_PD="${BOPOS_ASSETS_PD:-}"
    export BOPOS_ASSETS
    pd -nogui -jack -open "$PATCH_PATH/$ENTRYPOINT" \
        -send "; bopos-context seed $BOPOS_SEED; bopos-context run-id $BOPOS_RUN_ID; bopos-context patch $ACTIVE_PATCH; bopos-context assets $BOPOS_ASSETS_PD; bopos-context version $BOPOS_VERSION; bopos-context patch-fingerprint $BOPOS_PATCH_FINGERPRINT" \
        >"$OUTDIR/pd-$LABEL.log" 2>&1 &
    PD_PID=$!
    sleep 5

    if ! kill -0 "$PD_PID" 2>/dev/null; then
        echo "pd exited early for $LABEL (see $OUTDIR/pd-$LABEL.log); skipping"
    else
        python3 "$SCRIPT_DIR/perf_measure.py" run \
            --duration "$DURATION" --label "$LABEL" --patch "$ACTIVE_PATCH" \
            --jack-log "$JACKLOG" --out "$REPORT"
    fi

    kill "$PD_PID" 2>/dev/null; wait "$PD_PID" 2>/dev/null
    kill "$JACK_PID" 2>/dev/null; wait "$JACK_PID" 2>/dev/null
    sleep 2
done

echo ""
echo "=== matrix complete ==="
python3 "$SCRIPT_DIR/perf_measure.py" summarize "$REPORT"
echo "Audio stack left stopped; restart with bash/start-engine.sh"
