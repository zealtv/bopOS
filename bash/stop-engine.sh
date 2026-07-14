#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"
STOP_TIMEOUT="${BOPOS_STOP_TIMEOUT:-15}"

wait_for_exit() {
    pid="$1"
    timeout="$2"
    elapsed=0
    while kill -0 "$pid" 2>/dev/null; do
        if [ "$elapsed" -ge "$timeout" ]; then
            return 1
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 0
}

stop_process() {
    pidfile="$1"
    name="$2"
    if [ -f "$pidfile" ]; then
        pid="$(cat "$pidfile")"
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            if ! wait_for_exit "$pid" "$STOP_TIMEOUT"; then
                echo "WARNING: $name ($pid) did not stop within ${STOP_TIMEOUT}s; killing it" >&2
                kill -KILL "$pid" 2>/dev/null || true
                if ! wait_for_exit "$pid" 2; then
                    echo "ERROR: $name ($pid) is still running" >&2
                    return 1
                fi
            fi
        fi
        rm -f "$pidfile"
    else
        pkill -x "$name" 2>/dev/null || true
    fi
    return 0
}

if [ -f "$RUN_DIR/engine.pid" ]; then
    engine_name="$(cat "$RUN_DIR/engine.name" 2>/dev/null || true)"
    [ -n "$engine_name" ] || engine_name="engine"
    stop_process "$RUN_DIR/engine.pid" "$engine_name" || exit 1
fi
rm -f "$RUN_DIR/engine.pid" "$RUN_DIR/engine.name"

stop_process "$RUN_DIR/pd.pid" pd || exit 1
stop_process "$RUN_DIR/jackd.pid" jackd || exit 1
