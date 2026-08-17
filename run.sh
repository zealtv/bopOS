#!/bin/bash
#
# run.sh — start the bopOS dashboard on this laptop.
#
# Runs dashboard/server.py from the ~/.venvs/bopos virtualenv, bound to all
# interfaces (--host 0.0.0.0) so real nodes on the venue LAN can reach it. This
# is the one command a composer needs after ./install-dashboard.sh; open the printed URL.
# Press Ctrl-C to stop.
#
# Open the printed LAN address, not 0.0.0.0 — nodes are told to fetch patches
# from whichever address you browse to, and 0.0.0.0 means "this node" to them.
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
    echo "run.sh: no venv at $VENV — run ./install-dashboard.sh first." >&2
    exit 1
fi

# The address the operator opens is the address nodes are told to fetch patches
# from, so print one a node can actually reach. --port is honoured; 0.0.0.0 is
# never printed (a node resolves it as itself — incident 2026-08-17).
PORT=8080
prev=""
for arg in "$@"; do
    case "$arg" in
        --port=*) PORT="${arg#--port=}" ;;
        *) [ "$prev" = "--port" ] && PORT="$arg" ;;
    esac
    prev="$arg"
done

lan_addresses() {
    if command -v ip >/dev/null 2>&1; then
        ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1
    else
        ifconfig 2>/dev/null | awk '/inet /{print $2}'
    fi | grep -v '^127\.' | grep -v '^169\.254\.' | sort -u
}

# Ordinary venue LANs are RFC1918; list those first so a VPN address (100.64/10
# and friends) never leads.
ALL="$(lan_addresses || true)"
PRIVATE="$(printf '%s\n' "$ALL" | grep -E '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)' || true)"
OTHER="$(printf '%s\n' "$ALL" | grep -Ev '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)' | grep . || true)"
ADDRESSES="$(printf '%s\n%s\n' "$PRIVATE" "$OTHER" | grep . || true)"
COUNT="$(printf '%s\n' "$ADDRESSES" | grep -c . || true)"

if [ "$COUNT" -eq 1 ]; then
    echo "==> Dashboard on http://$ADDRESSES:$PORT/  ·  Ctrl-C to stop"
elif [ "$COUNT" -gt 1 ]; then
    # Several plausible interfaces — say so rather than pick one confidently.
    echo "==> Dashboard starting  ·  Ctrl-C to stop"
    echo "    Open the address on your venue LAN — nodes fetch patches from whichever you use:"
    printf '%s\n' "$ADDRESSES" | sed "s|^|      http://|;s|$|:$PORT/|"
else
    echo "==> Dashboard on http://localhost:$PORT/  ·  Ctrl-C to stop"
    echo "    No LAN address found; real nodes need one — see --public-url in dashboard/README.md."
fi
if [ "$COUNT" -gt 0 ]; then
    echo "    http://localhost:$PORT/ works too. Do not open http://0.0.0.0:$PORT/."
fi

exec "$PYTHON" "$SCRIPT_DIR/dashboard/server.py" --host 0.0.0.0 "$@"
