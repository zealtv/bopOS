# plantsOS Web Dashboard — Development Context

This document is a self-contained reference for building the plantsOS web
dashboard. It covers the existing system architecture, the OSC protocol, device
lifecycle, and the full dashboard design. A developer should be able to pick
this up cold and start building.


## 1. What plantsOS Is

plantsOS is a distributed sound installation framework. Multiple Raspberry Pis,
each with a speaker and optional sensors, run Pure Data audio patches
autonomously. A laptop on the same WiFi network monitors and controls them.

**Current control surface:** A Pure Data patch (DASHBOARD.pd) running on the
laptop. It works but is hard to extend, can't run on an iPad, and requires PD
knowledge to modify.

**Goal:** Replace DASHBOARD.pd with a web-based dashboard that runs in any
browser, supports iPad facilitator use, and speaks the exact same OSC protocol
so no Pi-side changes are needed.


## 2. Existing System Architecture

### Per-Pi process stack (started by bash/start.sh)

```
┌─────────────────────────────────────────────────────┐
│  Raspberry Pi                                        │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Pure Data (no GUI, via JACK)                 │   │
│  │  ├─ patches/<active>/main.pd  (user patch)   │   │
│  │  ├─ pd/bopos.osc.pd          (OSC routing)   │   │
│  │  └─ pd/bopos.feedback.pd     (audio feedback)│   │
│  ├──────────────────────────────────────────────┤   │
│  │  helper.py        │  io/main.py              │   │
│  │  (system admin)   │  (I2C sensor bridge)     │   │
│  ├──────────────────────────────────────────────┤   │
│  │  JACK audio server (ALSA, 44.1kHz, 512 buf)  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Boot sequence (bash/start.sh)

1. Read MAC address from `wlan0` (or `eth0`)
2. Read active patch from `patches/active_patch.txt`
3. Wait 15s for WiFi (skippable with keypress)
4. Start `helper.py $MACADDRESS` in background (listens on localhost:7770)
5. Start `io/main.py` in background (listens on localhost:8880)
6. Start JACK audio server (`jackd -P70 -p16 -t2000 -d alsa -dhw:DigiAMP -p 512 -n 2 -r 44100 -s -P`)
7. Wait 5s for JACK
8. Start Pure Data (`pd -nogui -jack -open "$PATCH_ENTRYPOINT" -send "..."`)
9. Run patch-specific `start.sh` if it exists

Startup messages sent to PD: `RANDOM`, `STARTTIME` (HHMMSS), `STARTDATE` (YYYYMMDD), `ACTIVEPATCH`

### Shutdown (bash/stop.sh)

```bash
pkill pd
pkill jackd
pkill python
```

### File layout on each Pi

```
/home/pi/plantsOS/
├── bash/
│   ├── start.sh              # Boot sequence
│   ├── stop.sh               # Kill all processes
│   ├── update.sh             # Git pull + reboot
│   ├── checkout.sh           # Git checkout branch
│   ├── getsamples.sh         # Download sample packs
│   ├── pull_active_patch.sh  # Git pull active patch
│   ├── clearsamples.sh       # Remove sample packs
│   ├── start-laptop.sh       # Laptop dev workflow
│   └── stop-laptop.sh        # Laptop dev stop
├── python/
│   ├── helper.py             # System admin OSC handler
│   └── io/
│       ├── main.py           # I2C-to-OSC bridge
│       ├── io_ads1015.py     # 4-channel ADC peripheral
│       ├── io_lis3dh.py      # 3-axis accelerometer peripheral
│       ├── io_mpr121.py      # 12-channel capacitive touch peripheral
│       └── io_template.py    # Template for new peripherals
├── pd/
│   ├── bopos.osc.pd          # OSC routing and heartbeat
│   ├── bopos.gui.pd          # Per-device dashboard widget (current PD dashboard)
│   ├── bopos.feedback.pd     # Audio feedback (aloha, reboot, shutdown sounds)
│   └── bop/                  # Shared PD abstractions library
├── patches/
│   ├── active_patch.txt      # Single line: name of current patch
│   └── default/
│       ├── main.pd           # Patch entry point (REQUIRED)
│       ├── bopos.config      # Patch config (e.g. SAMPLEPACKSURL)
│       └── start.sh          # Optional patch-specific init script
├── bopos.devices             # MAC → hostname/ID/position mapping
├── DASHBOARD.pd              # Current laptop dashboard (to be replaced)
└── MAIN.pd                   # (legacy, not used — patches/default/main.pd is the entrypoint)
```


## 3. OSC Protocol — Complete Reference

All communication between the laptop and Pis is OSC over UDP broadcast.

### Port Map

| Port | Who listens        | Who sends          | Direction           |
|------|--------------------|--------------------|---------------------|
| 5550 | Dashboard (laptop) | All Pis            | Pi → Dashboard      |
| 6660 | All Pis (bopos.osc)| Dashboard (laptop) | Dashboard → Pi      |
| 6661 | PD (bopos.osc)     | helper.py          | localhost only       |
| 6662 | PD (bopos.osc)     | io/main.py         | localhost only       |
| 7770 | helper.py          | PD (bopos.osc)     | localhost only       |
| 8880 | io/main.py         | PD (bopos.osc)     | localhost only       |

**The dashboard only needs ports 5550 (listen) and 6660 (send).** Ports 6661,
6662, 7770, and 8880 are localhost-only on each Pi.

### Messages FROM Pis → Dashboard (port 5550)

These arrive as UDP broadcast. The dashboard listens on port 5550.

| Message            | Payload              | Frequency    | Purpose                        |
|--------------------|----------------------|--------------|--------------------------------|
| `/hb`              | (none)               | Every 10s    | Heartbeat — device is alive    |
| `/aloha 1`         | int: 1               | On boot/request | Device announcing itself    |
| `/version <n>`     | float: version       | With heartbeat | Software version number     |
| `/id <n>`          | float: device ID     | After config | Device reporting its assigned ID |
| `/echo <0\|1>`     | int: 0 or 1          | On change    | Echo effect state              |
| `/rpt ...`         | varies               | On request   | Report/status data             |

**Note:** All outbound Pi messages are sent via `netsend -u -b` to
`255.255.255.255:5550` (UDP broadcast). The dashboard sees all of them on one
port. Messages currently don't include the device's MAC or ID in the heartbeat
payload — the dashboard must correlate devices by tracking which IP sent the
heartbeat, or rely on the `/id` message that follows `/aloha`.

### Messages FROM Dashboard → Pis (port 6660)

Sent as UDP broadcast to `255.255.255.255:6660`. All Pis receive all messages.
Routing by device ID happens inside `bopos.osc.pd`.

**Per-device commands (routed by ID):**

| Message                         | Args                   | Action                          |
|---------------------------------|------------------------|---------------------------------|
| `/<id>/gain <v>`                | float 0-1              | Set main volume                 |
| `/<id>/gain2 <v>`              | float 0-1              | Set secondary gain              |
| `/<id>/backing <v>`            | float 0-1              | Set backing track level         |
| `/<id>/echo <v>`               | int 0 or 1             | Toggle echo effect              |
| `/<id>/helper/update`          | (none)                 | System update (git pull + reboot) |
| `/<id>/helper/shutdown`        | (none)                 | Power off                       |
| `/<id>/helper/reboot`          | (none)                 | Reboot                          |
| `/<id>/helper/patch <name>`    | string: patch name     | Switch active patch             |
| `/<id>/helper/addpatch <u> <r>`| string: user, repo     | Clone patch from GitHub         |
| `/<id>/helper/pullpatch`       | (none)                 | Git pull active patch           |
| `/<id>/helper/getsamples`      | (none)                 | Download sample pack            |
| `/<id>/helper/config`          | (none)                 | Re-read bopos.devices, set hostname |
| `/<id>/aloha 1`                | int: 1                 | Request aloha announcement      |

**Broadcast commands (all devices):**

| Message                  | Action                              |
|--------------------------|-------------------------------------|
| `/all/gain <v>`          | Set volume on ALL devices           |
| `/all/helper/update`     | Update ALL devices                  |
| `/all/helper/shutdown`   | Shut down ALL devices               |
| `/all/helper/reboot`     | Reboot ALL devices                  |
| `/all/helper/patch <n>`  | Switch patch on ALL devices         |
| `/all/...`               | Any per-device command, broadcast   |

**I/O commands (forwarded to io/main.py on each Pi):**

| Message                              | Args                          | Action                    |
|--------------------------------------|-------------------------------|---------------------------|
| `/<id>/io/create <name> <type> <addr>` | string, string, hex string | Create I2C peripheral     |
| `/<id>/io/poll <rate>`               | float: Hz                     | Set sensor polling rate   |
| `/<id>/io/report`                    | (none)                        | Print active peripherals  |

### OSC Message Routing Inside bopos.osc.pd

```
Port 6660 (incoming from dashboard)
  → oscparse
  → route /all
    → if /all: strip prefix, process for this device
    → else: split first element as ID
      → route-by-id subpatch: compare against this device's ID
        → match: strip ID, send to [s osc-in]
        → no match: discard
  → osc-in bus routes to:
    → /helper/* → forward to helper.py on localhost:7770
    → /io/*    → forward to io/main.py on localhost:8880
    → /gain, /echo, etc. → internal PD routing to patch
```

### How Heartbeat Tracking Works in Current Dashboard

1. Each Pi sends `/hb` every 10 seconds via UDP broadcast to port 5550
2. The heartbeat is preceded by `/rpt` which includes the device ID
3. DASHBOARD.pd routes by ID to the matching `bopos.gui` subpatch
4. The subpatch blinks an indicator on receipt

**For the new dashboard:** Track heartbeats per source IP. Correlate IP → device
after seeing an `/id` message from that IP. Mark a device as offline after ~30s
without a heartbeat.


## 4. Device Identity

### bopos.devices file format

```csv
MAC, hostname, ID,  POSL, POSR
b8:27:eb:b4:64:79, bobop, 111, 0 0, 0 0
b8:27:eb:2c:73:80, spool1, 1, 0 0, 0 100
b8:27:eb:d3:e9:2e, spool2, 2, 100 0, 100 100
d8:3a:dd:9b:56:41, voice1, 1, 0 0, 0 0
```

Parsed by `helper.py` using Python's `csv.reader` with `skipinitialspace=True`.
Fields: MAC address, hostname, numeric ID, position 1 (x y), position 2 (x y).

**Identity flow:**
1. `start.sh` reads MAC from `/sys/class/net/wlan0/address`
2. Passes MAC as `sys.argv[1]` to `helper.py`
3. On boot, bopos.osc.pd sends `/helper/config` to helper.py
4. helper.py reads `bopos.devices`, finds matching MAC row
5. Sets hostname via `hostnamectl`, updates `/etc/hosts`, restarts avahi
6. Sends `/id <float>` to PD on localhost:6661
7. PD stores ID, uses it for routing and heartbeat identification

### Patch system

- Active patch stored in `patches/active_patch.txt` (single line, just the folder name)
- Each patch is a folder under `patches/` with at minimum a `main.pd` file
- Patches can optionally include `bopos.config` (shell variables) and `start.sh`
- Patch switching: helper.py writes new name to `active_patch.txt`, then runs
  `setsid bash -c 'stop.sh; sleep 2; start.sh'` (detached, survives pkill python)
- Patches are git repos, added via `git clone --recursive` from GitHub

### Available I2C peripherals

| Type     | Module          | Description                    | Channels | Default addr |
|----------|-----------------|--------------------------------|----------|--------------|
| ads1015  | io_ads1015.py   | 12-bit ADC, 4 analog inputs    | 4        | 0x48         |
| lis3dh   | io_lis3dh.py    | 3-axis accelerometer           | 3 (x,y,z)| auto         |
| mpr121   | io_mpr121.py    | 12-channel capacitive touch    | 12       | 0x5A         |

Created at runtime via OSC: `/io/create <name> <type> <address>`
Polled at configurable rate (default 10 Hz), sent as OSC bundle to PD on port 6662.


## 5. Current Dashboard (DASHBOARD.pd) — What We're Replacing

DASHBOARD.pd runs on the laptop. It contains:

- An `osc` subpatch that:
  - Listens on port 5550 for Pi broadcasts
  - Sends to `255.255.255.255:6660` to command all Pis
- Multiple `bopos.gui <id>` instances, one per device
- A `message` subpatch documenting the OSC API

**Each bopos.gui instance provides:**
- Update button → sends `/helper/update`
- Shutdown button → sends `/helper/shutdown`
- Reboot button → sends `/helper/reboot`
- Gain slider (0-1) → sends `/gain <value>`
- Gain2 slider (0-1) → sends `/gain2 <value>` (via label, not hsl)
- Backing slider (0-1) → sends `/backing <value>` (via label, not hsl)
- Echo toggle → sends `/echo <0|1>`
- Get Samples button → sends `/helper/getsamples`
- Aloha button → sends `/aloha 1`
- Heartbeat indicator (blinks on `/hb`)
- Version display
- Print toggle (debug)
- Status list box

**Limitations:**
- Fixed number of device slots (manually add `bopos.gui N` instances)
- No spatial view
- No iPad support
- No presets
- No device auto-discovery
- Requires Pure Data to run


## 6. New Dashboard Design

### Tech Stack

| Layer    | Choice                 | Rationale                                    |
|----------|------------------------|----------------------------------------------|
| Backend  | Python 3 + FastAPI     | Async, WebSocket-native, same language as Pi code |
| OSC lib  | python-osc             | Already used on the Pi side (as pyOSC3)      |
| Frontend | Vanilla HTML/JS/CSS    | No build step, no node_modules, artist-readable |
| Spatial  | SVG (inline in HTML)   | Draggable elements, styleable with CSS       |
| State    | JSON file on disk      | No database, human-readable, git-friendly    |
| Serve    | FastAPI static files   | One process, one port, no nginx              |

No React/Vue/Svelte — the UI has ~3 views and ~20 interactive elements. A
framework adds a build step and conceptual overhead for something that doesn't
need it. No Electron — we just need a browser tab.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Laptop / any machine on the installation network            │
│                                                              │
│  ┌──────────────┐        ┌─────────────────────────────────┐ │
│  │  Browser      │◄─ WS ─►│  Python backend (FastAPI)      │ │
│  │  (Tech view)  │        │                                 │ │
│  └──────────────┘        │  ├─ WebSocket hub (↔ browsers)  │ │
│                           │  ├─ OSC listener  (port 5550)   │ │
│  ┌──────────────┐        │  ├─ OSC sender   (port 6660)    │ │
│  │  iPad Safari  │◄─ WS ─►│  └─ JSON state file            │ │
│  │  (Facilitator)│        │                                 │ │
│  └──────────────┘        └─────────────────────────────────┘ │
└──────────────────────────┼───────────────────────────────────┘
                      OSC  │  UDP broadcast
          ┌────────┬───────┼──────┬────────┐
          │        │       │      │        │
       ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
       │ Pi 1│ │ Pi 2│ │ Pi 3│ │ Pi 4│ │ Pi 5│
       └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
```

The backend is the single bridge between browsers (HTTP/WebSocket) and Pis
(OSC/UDP). All intelligence lives in the backend; browsers are thin views.

### File structure

```
dashboard/
├── server.py              # FastAPI app, routes, WebSocket hub, OSC bridge
├── state.py               # State management, JSON persistence
├── osc_bridge.py          # OSC send/receive, protocol translation
├── requirements.txt       # fastapi, uvicorn, python-osc
├── static/
│   ├── index.html         # Technical dashboard
│   ├── facilitator.html   # Facilitator view (iPad-optimised)
│   ├── css/
│   │   └── style.css      # Shared styles (dark theme, responsive)
│   └── js/
│       ├── dashboard.js   # Technical dashboard logic
│       ├── facilitator.js # Facilitator view logic
│       ├── spatial.js     # SVG spatial map (drag, drop, position)
│       └── ws.js          # WebSocket connection manager
└── installation.json      # Per-installation state (gitignored)
```

### Running it

```bash
cd dashboard
pip install -r requirements.txt
python server.py
# Serving on http://0.0.0.0:8080
# Technical dashboard: http://localhost:8080/
# Facilitator view:    http://localhost:8080/facilitator
```

On iPad: connect to same WiFi, open `http://<laptop-ip>:8080/facilitator`.
Add to home screen for fullscreen PWA experience.

No build step. No compilation. No Docker. One command.


## 7. WebSocket Protocol (Browser ↔ Backend)

JSON messages over WebSocket. Simple type + data structure.

### Backend → Browser (state updates)

```json
{"type": "state",         "data": {"name": "Botanic 2026", "devices": {...}, "presets": {...}}}
{"type": "device_online", "data": {"mac": "b8:27:eb:xx:xx:xx", "ip": "192.168.1.42"}}
{"type": "device_offline","data": {"mac": "b8:27:eb:xx:xx:xx"}}
{"type": "device_update", "data": {"mac": "b8:27:eb:xx:xx:xx", "gain": 0.75}}
{"type": "heartbeat",     "data": {"mac": "b8:27:eb:xx:xx:xx", "timestamp": 1709000000}}
```

On connect, the backend sends a full `state` message so the browser has
everything immediately. After that, incremental updates only.

### Browser → Backend (user actions)

```json
{"type": "set_gain",      "data": {"id": 1, "value": 0.75}}
{"type": "set_gain2",     "data": {"id": 1, "value": 0.5}}
{"type": "set_backing",   "data": {"id": 1, "value": 0.6}}
{"type": "set_echo",      "data": {"id": 1, "value": 1}}
{"type": "switch_patch",  "data": {"id": 1, "patch": "wind_chimes"}}
{"type": "reboot",        "data": {"id": 1}}
{"type": "shutdown",      "data": {"id": 1}}
{"type": "update",        "data": {"id": 1}}
{"type": "get_samples",   "data": {"id": 1}}
{"type": "aloha",         "data": {"id": 1}}
{"type": "set_position",  "data": {"mac": "b8:27:eb:xx:xx:xx", "pos1": [2.5, 1.0], "pos2": [3.0, 1.0]}}
{"type": "assign_device", "data": {"mac": "b8:27:eb:xx:xx:xx", "id": 3, "name": "planter-nw"}}
{"type": "load_preset",   "data": {"name": "afternoon-full"}}
{"type": "save_preset",   "data": {"name": "morning-quiet"}}

// Broadcast variants — use "all" as id
{"type": "set_gain",      "data": {"id": "all", "value": 0.5}}
{"type": "reboot",        "data": {"id": "all"}}
```

The backend translates each message to the appropriate OSC message and sends it
to port 6660. It also updates its internal state and broadcasts the change to
all connected browsers.


## 8. State File: installation.json

```json
{
  "name": "Botanic Gardens 2026",
  "devices": {
    "b8:27:eb:b4:64:79": {
      "id": 1,
      "name": "planter-northwest",
      "pos1": [2.5, 1.0],
      "pos2": [3.0, 1.0],
      "patch": "default",
      "gain": 0.75,
      "gain2": 0.3,
      "backing": 0.8,
      "echo": 0
    },
    "b8:27:eb:2c:73:80": {
      "id": 2,
      "name": "planter-northeast",
      "pos1": [8.0, 1.0],
      "pos2": [8.5, 1.0],
      "patch": "default",
      "gain": 0.65,
      "gain2": 0.3,
      "backing": 0.8,
      "echo": 0
    }
  },
  "presets": {
    "morning-quiet": {
      "b8:27:eb:b4:64:79": {"gain": 0.3},
      "b8:27:eb:2c:73:80": {"gain": 0.3}
    },
    "afternoon-full": {
      "b8:27:eb:b4:64:79": {"gain": 1.0},
      "b8:27:eb:2c:73:80": {"gain": 1.0}
    }
  }
}
```

This file is the dashboard's source of truth. Keyed by MAC address (globally
unique, never changes). It is:
- Human-readable and hand-editable in an emergency
- Git-friendly (can be version-controlled per-installation)
- Swappable — the technician can load different `installation.json` files for
  different venues
- Presets store only the values they override; unspecified values are left as-is

On startup, the dashboard can also read `bopos.devices` to pre-populate the
device map during migration from the PD dashboard.


## 9. User Interface Design

### Technical Dashboard — `/`

The primary view for the artist or technician.

```
┌─────────────────────────────────────────────────────────────────┐
│  plantsOS                                    [Installation ▼]   │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                  │
│  DEVICES     │              SPATIAL VIEW                        │
│              │                                                  │
│  ● planter-nw│         ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐               │
│  ● planter-ne│         │                       │               │
│  ● planter-e │         │  [nw]          [ne]   │               │
│  ○ planter-s │         │                       │               │
│  ● planter-c │         │       [c]             │               │
│              │         │                       │               │
│──────────────│         │  [e]                   │               │
│  UNASSIGNED  │         │                       │               │
│  ○ b8:27:eb..│         │            [s]  ○     │               │
│              │         │                       │               │
│              │         └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘               │
│              │                                                  │
├──────────────┴──────────────────────────────────────────────────┤
│  SELECTED: planter-nw (ID 1)                    Patch: default  │
│                                                                 │
│  Gain ──────────●──────── 75%     Echo [ON ]                    │
│  Gain2 ────●──────────── 30%     Backing ────────●──── 80%     │
│                                                                 │
│  [Reboot]  [Shutdown]  [Update]  [Get Samples]  [Patch ▼]     │
└─────────────────────────────────────────────────────────────────┘
```

**Spatial map:** SVG. Devices are circles, draggable. Color = status (green
online, gray offline, amber recently lost). Click to select.

**Device list:** All known devices. Click to select. Unassigned devices (seen
via heartbeat but not in `installation.json`) shown separately.

**Detail panel:** Controls for selected device. Mirrors bopos.gui.pd: gain,
gain2, backing sliders, echo toggle, action buttons, patch selector.

**Assign flow:** Unassigned device appears in sidebar. Give it a name and ID.
Drag to position on the spatial map.

### Facilitator View — `/facilitator`

Stripped-down, touch-optimised for non-technical facilitators on iPad.

```
┌─────────────────────────────────────────────────────────────────┐
│  plantsOS                                       4 / 5 online    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Northwest Planter          ████████████░░░░  80%    ●  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Northeast Planter          ██████████░░░░░░  65%    ●  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  East Planter               ████████████░░░░  80%    ●  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  South Planter              ░░░░░░░░░░░░░░░░  --     ○  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Centre Planter             ████████████████  100%   ●  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Master Volume   ══════════════════●═══════  65%                │
│                                                                 │
│  [Start All]              [Silence All]           [Preset ▼]   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Volume sliders:** Full-width per card. Touch-drag. Large targets for iPad.

**Status dot:** Green = online, gray = offline. No technical detail.

**Master volume:** Scales all device volumes proportionally.

**Presets:** Named volume/state configurations. "Morning quiet", "Afternoon
full", "Wind down". Created by technician, used by facilitator.

**Silence All:** Sets all gains to 0. The panic button.

**Start All:** Sends aloha to all devices (audio confirmation they're alive).

**PWA support:** Add to iPad home screen → launches fullscreen, no Safari
chrome. Web app manifest + service worker for offline shell.

### Design Principles (both views)

- **Dark UI, light text.** Installations are in dim spaces.
- **No logins.** Private WiFi network — authentication adds friction for no gain.
- **Responsive.** Tech dashboard adapts to laptop screens. Facilitator view
  adapts to iPad portrait and landscape.
- **Real-time.** State changes propagate to all browsers within ~100ms via
  WebSocket. Laptop and iPad always in sync.


## 10. Key Implementation Considerations

### OSC Bridge

The backend must simultaneously:
1. **Listen** on UDP port 5550 for Pi heartbeats (non-blocking)
2. **Send** to UDP broadcast `255.255.255.255:6660` for Pi commands
3. **Serve** HTTP for static files and WebSocket connections

FastAPI with `asyncio` handles this naturally. The OSC listener runs as an async
task alongside the HTTP server. Use `python-osc`'s `AsyncIOOSCUDPServer` or
wrap the blocking server in a thread.

### Heartbeat Tracking

```python
# Pseudo-code for device status tracking
HEARTBEAT_TIMEOUT = 30  # seconds

devices_last_seen = {}  # mac -> timestamp

def on_heartbeat(source_ip, source_port):
    mac = ip_to_mac_lookup(source_ip)  # from installation.json or ARP
    devices_last_seen[mac] = time.time()
    broadcast_to_browsers({"type": "heartbeat", "data": {"mac": mac}})

def check_timeouts():
    now = time.time()
    for mac, last_seen in devices_last_seen.items():
        if now - last_seen > HEARTBEAT_TIMEOUT:
            broadcast_to_browsers({"type": "device_offline", "data": {"mac": mac}})
```

**Challenge:** Heartbeats don't include the device's MAC address — they come
from an IP. The backend needs to correlate IP → MAC. Options:
- Read the ARP table (`ip neigh` or `/proc/net/arp`)
- Wait for `/id` messages and associate the ID with the source IP
- Have Pis include their MAC in heartbeat messages (requires Pi-side change — avoid for now)

### Multi-Browser Sync

Multiple browsers (laptop Chrome + iPad Safari) connect simultaneously. The
backend is authoritative:

1. Browser sends action (e.g., `set_gain`)
2. Backend updates internal state
3. Backend sends OSC to Pi
4. Backend broadcasts updated state to ALL connected WebSocket clients
5. All browsers reflect the change

No conflict resolution needed — changes are small, atomic, and last-write-wins
is fine for volume sliders.

### Resilience

**Dashboard crashes:** Pis keep running autonomously. Dashboard restarts,
reloads `installation.json`, starts receiving heartbeats. State restored in
seconds.

**Pi goes offline:** Dashboard shows it as offline. When it returns, heartbeat
resumes, dashboard shows it as online.

**Network drops:** Pis continue playing. Dashboard shows all offline. Network
recovers, everything reconnects automatically.

**iPad disconnects:** Laptop unaffected. iPad reloads page, gets full state on
WebSocket connect.

**Guiding principle:** The installation must survive any single failure without
human intervention. The dashboard is for visibility and adjustment, never a
single point of failure.

### Latency

Volume change path: browser → WebSocket → Python → OSC UDP → Pi.
Expected latency on local WiFi: <50ms. Acceptable for real-time slider control.

For continuous slider drag, throttle WebSocket sends to ~30Hz (every ~33ms) to
avoid flooding. Backend can also coalesce rapid OSC sends.


## 11. TouchOSC Compatibility

TouchOSC can coexist with the web dashboard. Two options:

**Option A — Direct (no sync):** TouchOSC sends OSC directly to port 6660,
exactly like DASHBOARD.pd does today. Works immediately but changes aren't
reflected in the web dashboard.

**Option B — Via backend (full sync):** Dashboard backend exposes an additional
OSC input port (e.g., 5560). TouchOSC sends there. Backend processes, updates
state, forwards to Pis, notifies browsers. Everything stays in sync.

**Recommendation:** Build the web facilitator view first. It works on iPad
without installing anything, shows device status, and is always in sync. Only
add TouchOSC routing if someone specifically needs the tactile multi-touch
slider feel that TouchOSC provides.


## 12. Migration Strategy

### Phase 1 — Run alongside DASHBOARD.pd

Both dashboards listen on port 5550. Both send to port 6660. They coexist
because UDP broadcast allows multiple listeners. The web dashboard can be tested
without disrupting the existing workflow.

**Note:** Only ONE dashboard should send commands at a time to avoid conflicting
state. During migration, use the PD dashboard for commands and the web dashboard
for monitoring until confidence is established.

### Phase 2 — Replace DASHBOARD.pd

Once the web dashboard has feature parity with bopos.gui (gain, gain2, backing,
echo, reboot, shutdown, update, get samples, aloha, heartbeat), stop opening
DASHBOARD.pd. Keep it in the repo as reference.

### Phase 3 — Extend beyond PD capabilities

Add spatial map, facilitator view, presets, auto-discovery — features that
were impractical in Pure Data.


## 13. Implementation Phases

### Phase 1 — Core (replace DASHBOARD.pd)

- [ ] FastAPI server with OSC bridge (listen 5550, send 6660)
- [ ] WebSocket hub (connect, broadcast, full state on connect)
- [ ] Device list with online/offline status (heartbeat tracking)
- [ ] Per-device controls: gain, gain2, backing, echo sliders
- [ ] Per-device actions: reboot, shutdown, update, get samples, aloha
- [ ] State persistence to `installation.json`
- [ ] Import existing `bopos.devices` for initial device map
- [ ] Dark theme, responsive CSS

### Phase 2 — Spatial + Facilitator

- [ ] SVG spatial map with drag-to-position
- [ ] Facilitator view (`/facilitator`) with volume sliders
- [ ] Master volume control
- [ ] Preset system (save/load/activate)
- [ ] PWA manifest for iPad home screen

### Phase 3 — Discovery + Assignment

- [ ] Unassigned device pool (new MACs appear automatically)
- [ ] Assign flow: name, ID, drag to position from dashboard
- [ ] Push assignment to Pi via OSC
- [ ] Remove dependency on `bopos.devices`

### Phase 4 — Extended

- [ ] Patch management from dashboard (switch, add from GitHub, update)
- [ ] Per-device sensor data display (forward from port 6662)
- [ ] Installation file management (save/load/switch)
- [ ] Optional: scheduled presets (time-of-day automation)
- [ ] Optional: TouchOSC backend bridge (port 5560)
