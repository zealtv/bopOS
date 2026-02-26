# plantsOS Dashboard — Design Document

## Motivation

The current dashboard is a Pure Data patch (DASHBOARD.pd) with per-device
subpatches (bopos.gui.pd). It works but is brittle to extend, hard to use on
tablets, and tightly coupled to the PD environment. As installations grow in
scale and are increasingly facilitated by non-technical team members, we need
a dashboard that is:

- **Cross-platform** — runs on Mac, Linux, Windows, iPad
- **Two-audience** — full technical control AND a simplified facilitator view
- **Discoverable** — devices announce themselves; no manual MAC-address wrangling
- **Maintainable** — readable code, no specialised authoring environment
- **Zero-install for clients** — open a browser, done

Critically, the new dashboard must speak the **exact same OSC protocol** as
DASHBOARD.pd so that no changes are required on the Pi side. Both dashboards
can run side-by-side during migration.


## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Laptop / any machine on the installation network            │
│                                                              │
│  ┌──────────────┐        ┌─────────────────────────────────┐ │
│  │  Browser      │◄─ WS ─►│  Python backend                │ │
│  │  (Tech view)  │        │                                 │ │
│  └──────────────┘        │  FastAPI                        │ │
│                           │  ├─ WebSocket hub (browser ↔ state) │
│  ┌──────────────┐        │  ├─ OSC listener  (port 5550 in)│ │
│  │  iPad Safari  │◄─ WS ─►│  ├─ OSC sender   (port 6660 out)│ │
│  │  (Facilitator)│        │  └─ State store   (JSON file)  │ │
│  └──────────────┘        └─────────────────────────────────┘ │
└──────────────────────────┼───────────────────────────────────┘
                      OSC  │  UDP (same protocol as DASHBOARD.pd)
          ┌────────┬───────┼──────┬────────┐
          │        │       │      │        │
       ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
       │ Pi 1│ │ Pi 2│ │ Pi 3│ │ Pi 4│ │ Pi 5│
       └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
```

The backend is the **single bridge** between the browser world (HTTP/WebSocket)
and the OSC world (UDP). All intelligence lives in the backend; browsers are
thin views.


## Tech Stack

| Layer    | Choice                 | Rationale                                    |
|----------|------------------------|----------------------------------------------|
| Backend  | Python 3 + FastAPI     | Async, WebSocket-native, same language as Pi code |
| OSC      | python-osc             | Already used on the Pi side                  |
| Frontend | Vanilla HTML/JS/CSS    | No build step, no node_modules, artist-readable |
| Spatial  | SVG (inline in HTML)   | Draggable elements, styleable with CSS, no canvas complexity |
| State    | JSON file on disk      | No database to install, human-readable, git-friendly |
| Serve    | FastAPI static files   | One process, one port, no nginx              |

**Why no React / Vue / Svelte?**
This is a control surface, not a product. The UI has ~3 views and ~20 interactive
elements. A framework adds a build step, a node ecosystem, and conceptual overhead
for something that doesn't need it. Vanilla JS with a few hundred lines of
WebSocket glue is more maintainable in this context.

**Why not Electron?**
Electron bundles Chromium (~200 MB). We just need a browser tab. The laptop
already has a browser. An iPad already has Safari. Electron solves a problem we
don't have.


## Communication Protocol

### OSC — unchanged from current system

The backend speaks the same OSC as DASHBOARD.pd:

**Listening on port 5550 (from Pis):**
- `/hb` — heartbeat (every 10s per device)
- `/aloha 1` — device announcement on boot
- `/version <n>` — firmware/software version
- `/id <n>` — device reporting its ID
- `/echo <0|1>` — echo state feedback

**Sending to port 6660 (broadcast to all Pis):**
- `/<id>/gain <0-1>` — set volume
- `/<id>/gain2 <0-1>` — secondary gain
- `/<id>/backing <0-1>` — backing track level
- `/<id>/echo <0|1>` — toggle echo
- `/<id>/helper/patch <name>` — switch patch
- `/<id>/helper/addpatch <user> <repo>` — add patch from GitHub
- `/<id>/helper/pullpatch` — update current patch
- `/<id>/helper/update` — system update (git pull + reboot)
- `/<id>/helper/shutdown` — power off
- `/<id>/helper/reboot` — reboot
- `/<id>/helper/getsamples` — download sample pack
- `/all/...` — broadcast variant of any of the above

### WebSocket — new, between backend and browsers

JSON messages over WebSocket. Simple verb + payload structure:

```json
// Backend → Browser (state updates)
{"type": "devices",      "data": [{"id": 1, "name": "planter-nw", ...}, ...]}
{"type": "device_status","data": {"id": 1, "online": true, "last_hb": 1234567890}}
{"type": "device_update","data": {"id": 1, "gain": 0.75}}

// Browser → Backend (user actions)
{"type": "set_gain",     "data": {"id": 1, "value": 0.75}}
{"type": "set_gain2",    "data": {"id": 1, "value": 0.5}}
{"type": "set_backing",  "data": {"id": 1, "value": 0.6}}
{"type": "set_echo",     "data": {"id": 1, "value": 1}}
{"type": "switch_patch", "data": {"id": 1, "patch": "wind_chimes"}}
{"type": "reboot",       "data": {"id": 1}}
{"type": "shutdown",     "data": {"id": 1}}
{"type": "update",       "data": {"id": 1}}
{"type": "set_position", "data": {"id": 1, "pos1": [2.5, 1.0], "pos2": [3.0, 1.0]}}
{"type": "assign_device","data": {"mac": "b8:27:eb:xx:xx:xx", "id": 3, "name": "planter-nw"}}

// Broadcast variants
{"type": "set_gain",     "data": {"id": "all", "value": 0.5}}
```


## User Interface

### Technical Dashboard — `/`

The primary view for the artist or technician setting up and monitoring the
installation.

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

Key interactions:
- **Spatial map:** Devices shown as circles. Drag to reposition. Color indicates
  status (green = online, gray = offline, amber = recently lost). Click to select.
- **Device list:** All known devices. Click to select. Unassigned devices (seen
  via heartbeat but not yet given an ID/name) shown separately.
- **Detail panel:** Controls for the selected device. Sliders, buttons, patch
  selector. Mirrors the controls from bopos.gui.pd.
- **Assign flow:** Drag an unassigned device from the sidebar onto the spatial
  map, give it a name and ID. Dashboard sends the assignment to the Pi.

### Facilitator View — `/facilitator`

A stripped-down, touch-optimised view for non-technical team members on an iPad.
Large targets, obvious status, no jargon.

```
┌─────────────────────────────────────────────────────────────────┐
│  plantsOS                                       4 / 5 online    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Northwest Planter          ████████████░░░░  80%    ● │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Northeast Planter          ██████████░░░░░░  65%    ● │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  East Planter               ████████████░░░░  80%    ● │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  South Planter              ░░░░░░░░░░░░░░░░  --     ○ │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Centre Planter             ████████████████  100%   ● │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Master Volume   ══════════════════●═══════  65%                │
│                                                                 │
│  [▶  Start All]          [■  Silence All]         [Preset ▼]  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Key interactions:
- **Volume sliders:** Each device has a horizontal slider. Touch-drag to adjust.
  The slider is the full width of the card — easy to grab on a tablet.
- **Status dot:** Green = online, gray = offline. No other detail. Facilitators
  don't need to know why it's offline.
- **Master volume:** Scales all device volumes proportionally.
- **Presets:** Save and recall named volume/state configurations. "Morning quiet",
  "Afternoon full", "Wind down". Configured by the technician, used by the
  facilitator.
- **Silence All:** Immediately sets all gains to 0. The panic button.
- **Start All:** Sends aloha to all devices (triggers feedback sound so you can
  confirm they're alive).
- **PWA support:** Add to iPad home screen for fullscreen, app-like experience.
  No Safari chrome, no accidental navigation.

### Design Principles (both views)

- **Dark UI, light text.** Installations are often in dim spaces. A bright screen
  is distracting.
- **No logins.** This runs on a private WiFi network you control. Authentication
  adds friction for zero security benefit in this context.
- **Responsive.** The tech dashboard adapts to laptop screens. The facilitator
  view adapts to iPad portrait and landscape.
- **Real-time.** All state changes propagate to all connected browsers within
  ~100ms. If someone adjusts volume on the laptop, the iPad reflects it
  immediately.


## Auto-Discovery

### How it works today

1. MAC addresses are pre-registered in `bopos.devices`
2. Pi boots, helper.py reads `bopos.devices` to find its own MAC
3. Sets hostname and sends ID to MAIN.pd
4. MAIN.pd heartbeats with that ID to port 5550

### How it works with the new dashboard

1. Pi boots with a minimal identity (either from `/boot/firmware/bopos.conf`
   or just its MAC address — it heartbeats either way)
2. Dashboard receives heartbeat, identifies the device by MAC
3. If MAC is known (previously assigned): shows as online with its name/position
4. If MAC is unknown: shows in the "unassigned" pool
5. Technician assigns the device from the dashboard: gives it a name, ID, and
   drags it to a position on the spatial map
6. Dashboard sends assignment to the Pi via OSC
7. Pi stores assignment locally (survives reboot without needing the dashboard)
8. Dashboard persists assignment in its state file

### Transition period

During migration, `bopos.devices` can still be used as a fallback. The dashboard
reads it on startup to pre-populate its device map. As devices are discovered
and assigned through the dashboard, the state file becomes the source of truth.
Eventually `bopos.devices` becomes unnecessary.


## State Management

### State file: `installation.json`

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

This file is the dashboard's source of truth. It is:
- Human-readable and hand-editable in an emergency
- Git-friendly (can be version-controlled per-installation if desired)
- Loadable — the technician can swap `installation.json` files to switch between
  installations on the same laptop
- Exportable/importable from the dashboard UI


## Presets

Presets capture a snapshot of adjustable parameters across all devices. They
are designed for the facilitator workflow:

- **Technician creates presets** during setup: "morning", "afternoon", "evening",
  "wind down", "silent"
- **Facilitator selects presets** from a dropdown during the day
- **Presets can also be triggered on a schedule** (optional future feature)

A preset stores only the values it modifies. Unspecified values are left at their
current state. This allows "volume-only" presets and "patch-only" presets to
coexist.


## TouchOSC Compatibility

The dashboard backend speaks OSC. TouchOSC speaks OSC. They can coexist:

```
                    ┌─────────────┐
iPad TouchOSC ────►│             │
  (OSC direct)     │  Port 6660  │──── Pis
                    │  (broadcast) │
Dashboard      ────►│             │
  (OSC via backend)└─────────────┘
```

TouchOSC can talk directly to port 6660, bypassing the dashboard entirely. This
is exactly how the PD dashboard works today — the protocol is the same.

However, changes made via TouchOSC won't be reflected in the web dashboard
(it doesn't know about them). For full visibility, route TouchOSC through the
dashboard backend instead:

- Dashboard backend exposes an OSC input port (e.g., 5560)
- TouchOSC sends to that port
- Backend processes, updates state, forwards to Pis, notifies browsers

This keeps everything in sync. But it's an optional refinement — for a
facilitator who just needs volume sliders, the web facilitator view is simpler
to set up and maintain than a TouchOSC layout.


## Resilience

**If the dashboard crashes:** Pis keep running. They're autonomous — they run
their patches, play audio, read sensors. The dashboard is for monitoring and
adjustment, never for keeping things alive. When the dashboard restarts, it
reloads `installation.json` and starts receiving heartbeats again. State is
restored within seconds.

**If a Pi goes offline:** Dashboard shows it as offline (gray dot, faded card).
No error dialogs, no popups. When it comes back, it heartbeats and the dashboard
shows it as online again.

**If the network drops:** Pis continue playing. Dashboard shows all devices as
offline. When the network recovers, everything reconnects automatically. No
manual intervention.

**If the iPad disconnects:** The laptop dashboard is unaffected. When the iPad
reconnects and reloads the page, it gets current state immediately.

The guiding principle: **the installation must survive any single failure
without human intervention.** The dashboard makes things visible and adjustable,
but it's never a single point of failure for the installation itself.


## File Structure

```
dashboard/
├── server.py              # FastAPI backend, OSC bridge, WebSocket hub
├── state.py               # State management, JSON persistence
├── osc_bridge.py          # OSC send/receive, protocol translation
├── requirements.txt       # fastapi, uvicorn, python-osc
├── static/
│   ├── index.html         # Technical dashboard
│   ├── facilitator.html   # Facilitator view
│   ├── css/
│   │   └── style.css      # Shared styles (dark theme, responsive)
│   └── js/
│       ├── dashboard.js   # Technical dashboard logic
│       ├── facilitator.js # Facilitator view logic
│       ├── spatial.js     # SVG spatial map (drag, drop, position)
│       └── ws.js          # WebSocket connection manager
└── installation.json      # Per-installation state (gitignored)
```

Placed inside the plantsOS repo as `dashboard/`. Could be split to a separate
repo later if it grows, but co-location keeps the OSC protocol definitions in
sync during development.


## Running It

```bash
cd dashboard
pip install -r requirements.txt
python server.py
# → Serving on http://0.0.0.0:8080
# → Technical dashboard: http://localhost:8080/
# → Facilitator view:    http://localhost:8080/facilitator
```

On the iPad: connect to the same WiFi, open Safari, navigate to
`http://<laptop-ip>:8080/facilitator`. Optionally add to home screen for
fullscreen PWA experience.

No build step. No compilation. No Docker. One command.


## Implementation Phases

### Phase 1 — Core (replace DASHBOARD.pd)

- FastAPI server with OSC bridge
- Listen on 5550, send on 6660
- WebSocket hub
- Device list with online/offline status (heartbeat tracking)
- Per-device controls: gain, gain2, backing, echo
- Per-device actions: reboot, shutdown, update
- State persistence to JSON
- Import existing bopos.devices for initial device map

### Phase 2 — Spatial + Facilitator

- SVG spatial map with drag-to-position
- Facilitator view with volume sliders
- Master volume
- Preset system (save/load/activate)
- PWA manifest for iPad home screen

### Phase 3 — Discovery + Assignment

- Unassigned device pool (new MACs appear automatically)
- Assign flow: name, ID, drag to position
- Push assignment to Pi via OSC
- Remove dependency on bopos.devices

### Phase 4 — Extended Control

- Patch management from dashboard (switch, add from GitHub, update)
- Per-device sensor data display (I/O values from port 6662, forwarded)
- Installation file management (save/load/switch installations)
- Optional: scheduled presets (time-of-day automation)
