# bopOS

A Raspberry Pi and Arduino based framework for networked multichannel sound and more.   

# Requirements 

- A Raspberry Pi zero or above
- A Raspberry Pi soundcard

# bopOS uses
- puredata 0.54 vanilla 
- python3
- [pyOSC3](https://pypi.org/project/pyOSC3/)
- pd-comport (for arduino)


# Setup

## Prepare you bopOS project
- fork this repo and clone to your computer
```
git clone https://github.com/[yourUserName]/bopOS --recursive
```
- Edit \_Main.pd in Pure Data
- Edit rc.local, update.sh, and start.sh to point to your github repository
- commit and push your changes

## Flash SD using Raspberry Pi Imager
- OS: RASPBERRY PI OS LITE
- username: pi
- hostname: bop
- configure wireless LAN
- enable SSH
- Flash SD


# Installation 

## Install packages
- boot pi and login over ssh

```
ssh pi@bop.local
```

- update system 
- install jack2
- !!! (manually enable realtime priority for Jack when prompted)
- install git, pip, pure-data dependencies, pd-comport, 
- build and install puredata 0.54+
- copy PD externals to local folder
- install pyOSC to vitual environment

```
sudo apt-get update -y; 
sudo apt-get upgrade -y; 
sudo apt-get install -y jackd2;
sudo apt-get install -y git pip; 
sudo apt-get install -y build-essential automake autoconf libtool gettext libasound2-dev libjack-jackd2-dev tcl tk wish;
sudo apt-get install -y pd-comport;
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

## Install and configure your specific soundcard
on your pi:
- install your soundcard if required (usually involing editing config.txt)
- reboot pi
- list available soundcards
```
cat /proc/asound/cards
```

on your laptop:
- edit bopOS/scripts/start.sh to add you soundcard 
- save, commit changes and push to github

on your pi:
- goto home directory, clone this repo (or your fork)

```
cd ~; 
git clone https://github.com/zealtv/bopOS.git
```


# Update and reboot
run update script to
- pull lates changes from github
- download bop submodules
- copy rc.local start script to /etc
- reboot with jack, puredata, and helper.py running
- if you have speakers plugged in it might make a noise at this point

```
sudo ~/bopOS/scripts/update.sh
```