#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"

stop_process() {
    pidfile="$1"
    name="$2"
    if [ -f "$pidfile" ]; then
        kill "$(cat "$pidfile")" 2>/dev/null || pkill -x "$name" 2>/dev/null || true
        rm -f "$pidfile"
    else
        pkill -x "$name" 2>/dev/null || true
    fi
}

if [ -f "$RUN_DIR/engine.pid" ]; then
    if ! kill "$(cat "$RUN_DIR/engine.pid")" 2>/dev/null; then
        if [ -f "$RUN_DIR/engine.name" ]; then
            pkill -x "$(cat "$RUN_DIR/engine.name")" 2>/dev/null || true
        fi
    fi
fi
rm -f "$RUN_DIR/engine.pid" "$RUN_DIR/engine.name"

stop_process "$RUN_DIR/pd.pid" pd
stop_process "$RUN_DIR/jackd.pid" jackd
