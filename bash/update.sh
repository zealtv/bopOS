#!/bin/bash
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
echo "--- setting permissions to allow PD write access"
chown -R pi ./
cd bash
echo "--- copying rc.local"
sudo cp ./rc.local /etc/
echo "--- rebooting in 5 seconds..."
sleep 5
systemctl reboot