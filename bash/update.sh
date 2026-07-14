#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd /home/pi/bopOS
echo "--- saving active patch selection"
ACTIVE_PATCH=$(cat patches/active_patch.txt)
echo "--- clearing changes"
git restore .
echo "--- pulling from git"
git pull
echo "--- restoring active patch selection: $ACTIVE_PATCH"
echo "$ACTIVE_PATCH" > patches/active_patch.txt
echo "--- updating submodules"
git submodule update --init --recursive
echo "--- installing bopOS power authorization"
"$SCRIPT_DIR/install-power-control.sh"
echo "--- setting permissions to allow PD write access"
chown -R pi ./
cd bash
echo "--- copying rc.local"
sudo cp ./rc.local /etc/
echo "--- rebooting in 5 seconds..."
sleep 5
if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  /usr/bin/systemctl reboot
else
  /usr/bin/sudo -n /usr/bin/systemctl reboot
fi
