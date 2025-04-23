#!/bin/bash

#1.) get list of available soundcards by running:
#    cat /proc/asound/cards
#2.) edit the SOUNDCARD variable below as needed

#SOUNDCARD="YOUR_SOUNDCARD"
SOUNDCARD="sndrpihifiberry"
MACADDRESS=$(cat /sys/class/net/wlan0/address)
echo "MAC: $MACADDRESS"

sleep 5

#Start Jack 
jackd -P70 -p16 -t2000 -d alsa -dhw:$SOUNDCARD -p 128 -n 3 -r 44100 -s &
#jackd -P70 -p16 -t2000 -d alsa -dhw:$SOUNDCARD -p 128 -n 3 -r 22050 -s & #Jack at 22khz

# leave enough time for jack to start before launching PD
sleep 10

# PUREDATA
pd -nogui -jack -open "/home/pi/bopOS/pd/_MAIN.pd" -send "; RANDOM $RANDOM; " &

# leave enough time for PD to start before starting the helper  
# the helper will parse and forward variables from config.csv
sleep 5

# PYTHON
sudo /home/pi/venv/bin/python /home/pi/bopOS/scripts/helper.py $MACADDRESS &

exit