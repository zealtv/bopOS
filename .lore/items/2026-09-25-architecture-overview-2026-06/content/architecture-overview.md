# bopOS Architecture Notes

## Overview
Raspberry Pi + Pure Data framework for networked multi-device sound installations.

## KEY RULES
- **NEVER edit Pure Data patches (.pd files)** — PD programming is done by the user
- All PD work is the user's domain; we help with Python, Bash, and architecture

## Current driver: Kite Choir spool v2
- bopOS is being brought up to date with its fork plantsOS (2026-06), which ran ahead.
  This repo is now the canonical line; plantsOS systems migrate back to bopOS over time.
- Immediate target: a **Raspberry Pi Zero 2 W** running bopOS as the prototype spool brain
  *and* a standing bopOS dev rig (first time bopOS has run on a Pi Zero — expect tuning).
- Hardware: Pi Zero 2 W + DigiAmp+ (i2s) + HFS64 speaker, PiicoDev/Qwiic I2C bus
  (LIS3DH tilt + button + SSD1306 OLED status screen).
- Planned: **RSSI reporting as a first-class, switchable feature** (heartbeat + OLED).

## Installation History
- Earlier bopOS used ESP32 reading sensors → serial to Pd via the comport external.
  Those Arduino sketches are archived under `legacy/arduino/` (out of the boot path).
- Current system: **I2C direct to the Pi**, handled by Python (`io/main.py`).
- Several older installations still run previous versions.

## Core Components
1. **Pure Data (Pd)** — Audio synthesis and OSC routing (bopos.osc.pd, bopos.feedback.pd, bopos.gui.pd)
2. **bopos.py** — Admin service: shutdown, reboot, update, patch management (port 7770)
3. **io/main.py** — Sensor bridge: reads I2C peripherals, sends data to Pd via OSC (port 8880)
4. **bash scripts** — Boot, start/stop, update, sample management
5. **DASHBOARD.pd** — Laptop-side admin/control GUI

## OSC Port Map
| Port | Direction | Purpose |
|------|-----------|---------|
| 5550 | Pi → Laptop | Device status/heartbeat broadcast |
| 6660 | Laptop → Pi (broadcast) | Commands to devices |
| 6661 | bopos.py → Pd (localhost) | Helper responses |
| 6662 | io/main.py → Pd (localhost) | Sensor data |
| 7770 | Pd → bopos.py (localhost) | Admin commands |
| 8880 | Pd → io/main.py (localhost) | I/O commands |

## Boot Sequence
1. rc.local → start.sh (as pi user)
2. start.sh → bopos.py (background)
3. start.sh → io/main.py (background)
4. start.sh → jackd audio server
5. start.sh → Pure Data with active patch
6. start.sh → optional patch-specific start.sh

## Patch System
- Patches are git repos stored in patches/
- active_patch.txt holds current patch name
- Each patch has main.pd (entry point), optional bopos.config, optional start.sh
- Patches can be added from GitHub via /addpatch, switched via /patch, updated via /pullpatch
- **Known issue:** /patch command writes active_patch.txt but doesn't properly restart (start script issue)

## Supported I2C Peripherals
- ADS1015: 4-channel ADC (analog voltage)
- LIS3DH: 3-axis accelerometer (tilt angles)
- MPR121: 12-channel capacitive touch

## Device Identity
- bopos.devices CSV maps MAC address → hostname, ID, position
- bopos.py reads MAC, sets hostname, sends ID to Pd

## Key Dependencies
- jackd2 (audio server)
- Pure Data 0.54+ (audio/OSC processing)
- pyOSC3 (Python OSC)
- Adafruit CircuitPython libraries (sensor drivers)
- bop library (Pd abstractions for synthesis/sequencing)

## Development Pain Points
- No laptop dev workflow — need a start script for laptop that runs pd + io/main.py with MCP2221A USB
- Patch restart friction (manual messaging / script running needed)
- MPR121 tuning: had good values on ESP32 version but lost them, need low-friction way to retune

## Scaling
- Typical deployment: 2–12 Pis
- Should scale easily (feature of the system)

## README TODO Items (from project)
- Decouple bopos from PD patch (mostly done, some friction remains)
- Hot-swappable patches specified as git repos
- Install script
- Broadcast MAC/IP/hostname on boot
- Configure soundcard/jack via bopos.config
- bopos.py should just run bash scripts and talk OSC
