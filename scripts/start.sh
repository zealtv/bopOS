#!/bin/bash

#1.) get list of available soundcards by running: cat /proc/asound/cards
#2.) edit the SOUNDCARD variable below as needed

#SOUNDCARD="YOUR_SOUNDCARD"
SOUNDCARD="sndrpihifiberry"
#SOUNDCARD="IQaudIODAC"
#SOUNDCARD="DigiAMP"

RND=$RANDOM
MACADDRESS=$(cat /sys/class/net/wlan0/address)
# MACADDRESS=$(cat /sys/class/net/eth0/address)
now=$(date --iso-8601=seconds)
STARTDATE=$(date -d "$now" +%Y%m%d)
STARTTIME=$(date -d "$now" +%H%M%S)

echo "------------------- Waiting..."

sleep 10

echo "------------------- Starting bopOS..."
echo "SOUNDCARD: $SOUNDCARD"
echo "MAC ADDRESS: $MACADDRESS"
echo "RANDOM: $RND"
echo "STARTDATE: $STARTDATE"
echo "STARTTIME: $STARTTIME"


#Start Jack 
echo "------------------- Starting Jack..."
# jackd -P70 -p16 -t2000 -d alsa -dhw:$SOUNDCARD -p 512 -n 3 -r 44100 -s -P& #44.1khz        
jackd -P70 -p16 -t2000 -d alsa -dhw:$SOUNDCARD -p 512 -n 3 -r 22050 -s -P& #22khz

# leave enough time for jack to start before launching PD
sleep 15

echo "------------------- Starting Pure Data..."
# PUREDATA
pd -nogui -jack -open "/home/pi/bopOS/pd/_MAIN.pd" -send "; RANDOM $RND; STARTTIME $STARTTIME; STARTDATE $STARTDATE; " &

# leave enough time for PD to start before starting the helper  
# the helper will parse and forward variables from config.csv
sleep 5

echo "------------------- Starting helper.py..."
# PYTHON
sudo /home/pi/venv/bin/python /home/pi/bopOS/scripts/helper.py $MACADDRESS &

exit