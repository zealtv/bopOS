#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"

"$SCRIPT_DIR/stop-engine.sh"

stop_process() {
    pidfile="$1"
    pattern="$2"
    if [ -f "$pidfile" ]; then
        kill "$(cat "$pidfile")" 2>/dev/null || pkill -f "$pattern" 2>/dev/null || true
        rm -f "$pidfile"
    else
        pkill -f "$pattern" 2>/dev/null || true
    fi
}

stop_process "$RUN_DIR/helper.pid" "$BOPOS_DIR/python/helper.py"
stop_process "$RUN_DIR/io.pid" "$BOPOS_DIR/python/io/main.py"
