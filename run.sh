#!/bin/bash
#
# run.sh — start the bopOS dashboard on this laptop.
#
# Runs dashboard/server.py from the ~/.venvs/bopos virtualenv, bound to all
# interfaces (--host 0.0.0.0) so real nodes on the venue LAN can reach it. This
# is the one command a composer needs after ./install.sh; open the printed URL.
# Press Ctrl-C to stop.
#
# Any extra arguments are passed straight through to server.py, e.g.
#   ./run.sh --port 9000          (see dashboard/README.md for all flags)
#
# Override the venv location with BOPOS_VENV=/some/path ./run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="${BOPOS_VENV:-$HOME/.venvs/bopos}"
PYTHON="$VENV/bin/python"

case "${1:-}" in
    -h|--help) grep '^#' "$0" | grep -v '^#!' | sed 's/^# \{0,1\}//'; exit 0 ;;
esac

if [ ! -x "$PYTHON" ]; then
    echo "run.sh: no venv at $VENV — run ./install.sh first." >&2
    exit 1
fi

echo "==> Dashboard starting (default http://localhost:8080/  ·  Ctrl-C to stop)"
exec "$PYTHON" "$SCRIPT_DIR/dashboard/server.py" --host 0.0.0.0 "$@"
