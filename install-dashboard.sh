#!/bin/bash
#
# install-dashboard.sh — one-time laptop setup for running the bopOS dashboard.
#
# Creates the ~/.venvs/bopos virtualenv (the path every doc uses) and installs
# the dashboard's Python dependencies into it, so a composer never has to touch
# venvs or pip by hand. Idempotent: re-running just upgrades the packages.
#
# After this, start the dashboard with:  ./run.sh
#
# Override the venv location with:
# BOPOS_VENV=/some/path ./install-dashboard.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="${BOPOS_VENV:-$HOME/.venvs/bopos}"

case "${1:-}" in
    -h|--help) grep '^#' "$0" | grep -v '^#!' | sed 's/^# \{0,1\}//'; exit 0 ;;
    "") : ;;
    *) echo "install-dashboard.sh: unknown option '$1' (try --help)" >&2; exit 2 ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
    echo "install-dashboard.sh: python3 not found on PATH — install Python 3.11+ first." >&2
    exit 1
fi

if [ ! -d "$VENV" ]; then
    echo "==> Creating virtualenv at $VENV"
    python3 -m venv "$VENV"
else
    echo "==> Reusing existing virtualenv at $VENV"
fi

echo "==> Installing dashboard dependencies"
"$VENV/bin/pip" install --upgrade pip >/dev/null
"$VENV/bin/pip" install -r "$SCRIPT_DIR/dashboard/requirements.txt"

echo
echo "Done. Start the dashboard with:  ./run.sh"
