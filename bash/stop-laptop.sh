#!/bin/bash

# stop-laptop.sh — Stop bopOS laptop processes (no jackd)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOPOS_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$BOPOS_DIR/run"

if [ -f "$RUN_DIR/pd.pid" ]; then
    kill "$(cat "$RUN_DIR/pd.pid")" 2>/dev/null || pkill -x pd 2>/dev/null || true
    rm -f "$RUN_DIR/pd.pid"
else
    pkill -x pd 2>/dev/null || true
fi

if [ -f "$RUN_DIR/io.pid" ]; then
    kill "$(cat "$RUN_DIR/io.pid")" 2>/dev/null || pkill -f "$BOPOS_DIR/python/io/main.py" 2>/dev/null || true
    rm -f "$RUN_DIR/io.pid"
else
    pkill -f "$BOPOS_DIR/python/io/main.py" 2>/dev/null || true
fi
