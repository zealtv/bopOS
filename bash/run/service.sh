#!/bin/bash
# Internal foreground service entry point; people use /usr/local/bin/bopos.
set -euo pipefail
BOPOS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_DIR="$BOPOS_DIR/run"
mkdir -p "$RUN_DIR"
if [ -f "$BOPOS_DIR/bopos.config" ]; then
    source "$BOPOS_DIR/bopos.config"
fi
PYTHON_BIN=python3
[ ! -x "$HOME/venv/bin/python" ] || PYTHON_BIN="$HOME/venv/bin/python"
log_to() {
    "$PYTHON_BIN" "$BOPOS_DIR/python/logpipe.py" "$1" "${IO_LOG_MAX_BYTES:-134217728}"
}
case "${1:-}" in
    daemon)
        "$PYTHON_BIN" "$BOPOS_DIR/python/boot_state.py" "$RUN_DIR/audio-config.json"
        "$PYTHON_BIN" -u "$BOPOS_DIR/python/bopos.py" 2>&1 | log_to "$RUN_DIR/bopos.log"
        ;;
    io)
        cd "$BOPOS_DIR/python/io"
        "$PYTHON_BIN" -u "$BOPOS_DIR/python/io/main.py" 2>&1 | log_to "$RUN_DIR/io.log"
        ;;
    *) echo "Internal service entry point requires daemon or io" >&2; exit 2 ;;
esac
