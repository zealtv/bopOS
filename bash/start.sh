#!/bin/bash

#1.) get list of available soundcards by running: cat /proc/asound/cards
#2.) edit the SOUNDCARD variable below as needed

#SOUNDCARD="YOUR_SOUNDCARD"
# SOUNDCARD="sndrpihifiberry"
# SOUNDCARD="IQaudIODAC"
SOUNDCARD="DigiAMP"

RND=$RANDOM
MACADDRESS=$(cat /sys/class/net/wlan0/address)
# MACADDRESS=$(cat /sys/class/net/eth0/address) # for wired connection, use eth0 instead of wlan0
now=$(date --iso-8601=seconds)
STARTDATE=$(date -d "$now" +%Y%m%d)
STARTTIME=$(date -d "$now" +%H%M%S)


# sleep 15

echo "------------------- Waiting..."
# Wait up to 15 seconds, allow skip by key press
WAIT_TIME=15
SKIP=0
printf "Waiting %ds (press any key to skip)...\n" "$WAIT_TIME"
stty -echo -icanon time 0 min 0
for ((i=0; i<$WAIT_TIME; i++)); do
    read -t 1 -n 1 key && SKIP=1 && break
    printf "."
    sleep 1
done
stty sane
echo ""
if [ $SKIP -eq 1 ]; then
    echo "Wait skipped by key press."
else
    echo "Wait complete."
fi

echo "------------------- Starting bopOS..."
echo "SOUNDCARD: $SOUNDCARD"
echo "MAC ADDRESS: $MACADDRESS"
echo "RANDOM: $RND"
echo "STARTDATE: $STARTDATE"
echo "STARTTIME: $STARTTIME"

# Determine active patch
ACTIVE_PATCH=$(cat /home/pi/bopOS/patches/active_patch.txt)
PATCH_PATH="/home/pi/bopOS/patches/$ACTIVE_PATCH"
PATCH_ENTRYPOINT="$PATCH_PATH/main.pd" 

# Print the current active patch clearly
echo "====================="
echo "ACTIVE PATCH: $ACTIVE_PATCH"
echo "PATCH PATH: $PATCH_PATH"
echo "PATCH ENTRYPOINT: $PATCH_ENTRYPOINT"
echo "====================="



# Start helper.py to manage system functions
# NB: no sudo — start.sh runs as user `pi` (rc.local: `su pi -c`), and the `pi`
# user is in the i2c/gpio/audio groups, so these need no root. On images without
# passwordless sudo (e.g. Pi OS Trixie) a `sudo` here silently fails at boot.
echo "------------------- Starting helper.py..."
/home/pi/venv/bin/python /home/pi/bopOS/python/helper.py $MACADDRESS &

# Start io/main.py to access sensors and peripherals
echo "------------------- Starting io/main.py..."
( cd /home/pi/bopOS/python/io && /home/pi/venv/bin/python main.py ) &

sleep 1



#Start Jack 
echo "------------------- Starting Jack..."
jackd -P70 -p16 -t2000 -d alsa -dhw:$SOUNDCARD -p 512 -n 2 -r 44100 -s -P& #44.1khz        
# jackd -P80 -t2000 -d alsa -dhw:$SOUNDCARD -p 1024 -n 2 -r 22050 -s -P& #22khz



# Wait up to 15 seconds for Jack, allow skip by key press
WAIT_TIME=5
SKIP=0
printf "Waiting %ds for Jack (press any key to skip)...\n" "$WAIT_TIME"
stty -echo -icanon time 0 min 0
for ((i=0; i<$WAIT_TIME; i++)); do
    read -t 1 -n 1 key && SKIP=1 && break
    printf "."
    sleep 1
done
stty sane
echo ""
if [ $SKIP -eq 1 ]; then
    echo "Wait for Jack skipped by key press."
else
    echo "Wait for Jack complete."
fi


echo "------------------- Starting Pure Data..."
# PUREDATA
pd -nogui -jack -open "$PATCH_ENTRYPOINT" -send "; RANDOM $RND; STARTTIME $STARTTIME; STARTDATE $STARTDATE; ACTIVEPATCH $ACTIVE_PATCH" &


# run active patch start script if it exists
if [ -f "$PATCH_PATH/start.sh" ]; then
    echo "------------------- Running patch start script..."
    bash "$PATCH_PATH/start.sh"
else
    echo "------------------- No patch start script found, skipping..."
fi  

exit