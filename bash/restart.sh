#!/bin/bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
sudo bash "$SCRIPT_DIR/stop.sh"
bash "$SCRIPT_DIR/start.sh"
