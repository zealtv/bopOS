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

# The floor is checked, not just asserted. It used to say "3.11+" and verify
# only that python3 existed; on a fresh macOS the python3 on PATH is 3.9, the
# venv got built from it, and the mismatch surfaced much later as a supervisor
# dying at import with a bare TypeError (61). 3.9 is the measured floor -- the
# fast suite and a real editor supervisor both pass on it.
if ! command -v python3 >/dev/null 2>&1; then
    echo "install-dashboard.sh: python3 not found on PATH — install Python 3.9+ first." >&2
    exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    echo "install-dashboard.sh: python3 is $(python3 -c 'import platform; print(platform.python_version())'), but bopOS needs 3.9+." >&2
    echo "Install a newer Python, or point BOPOS_VENV at a venv built from one." >&2
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
