# bopOS

A Raspberry Pi and Arduino based framework for networked multichannel sound, light, and motion.   This repo provides scaffolding for the [bop](https://github.com/zealtv/bop) library for PD Vanilla. Python scripts provide admin services (updating, rebooting, shutdown). 

# Requirements 

- puredata 0.54 vanilla 
- python3
- [pyOSC3](https://pypi.org/project/pyOSC3/)

## Optional Requirements for Arduino
- pd-comport 

Reads distance sensor and controls lights and stepper motor.  Communicates with PD via SLIP encoded OSC over USB serial.

### Arduino Sketch Requires:
- https://github.com/thomasfredericks/MicroOsc
- https://github.com/qub1750ul/Arduino_SharpIR
- http://www.airspayce.com/mikem/arduino/AccelStepper/
- https://github.com/FastLED/FastLED


# Installation and Setup

## Prepare you sketch
- fork this repo and clone to your development machine
```
git clone https://github.com/[yourUserName]/bopOS --recursive
```
- Edit \_Main.pd in PD
- Edit rc.local, update.sh, and start.sh to point to your fork
- commit and push your changes

## Flash SD using Raspberry Pi Imager
- OS: RASPBERRY PI OS LITE
- username: pi
- hostname: bop
- configure wireless LAN
- enable SSH
- Flash SD

## Install packages
- boot pi and login over ssh
```
ssh pi@bop.local
```

- update system 
- install git, pip, pure-data dependencies, and pd-comport
- install jack2 and manually enable realtime priority
```
sudo apt-get update -y; 
sudo apt-get upgrade -y; 
sudo apt-get install -y git pip build-essential automake autoconf libtool gettext libasound2-dev libjack-jackd2-dev tcl tk wish pd-comport;
sudo apt-get install -y jackd2
```

- build and puredata 0.54+, add externals to local extra folder, install pyOSC to vitual environment
```
cd ~; 
git clone https://github.com/pure-data/pure-data.git; 
cd ./pure-data/; 
./autogen.sh; 
./configure --enable-jack; 
make; 
sudo make install; 
mkdir ~/pd-externals; 
cd ~/pd-externals; 
sudo cp -r /lib/pd/extra/* ./; 
sudo chown -R pi ./*; cd ~; 
python3 -m venv ./venv; 
./venv/bin/pip install pyOSC3
```

## Install project code

- goto home directory, clone this repo (or your fork)
```
cd ~; 
git clone https://github.com/zealtv/bopOS.git
```

- !copy samples
- !edit scripts/start.sh to configure soundcard
- run update script 
```
sudo ~/bopOS/scripts/update.sh
```

- pi should copy rc.local and reboot with jack, puredata, and helper.py running