# 30-dedicated-dashboard-port

**Asked:** Bob, 2026-11-04, in chat: "lets default bopOS to a dedicated
port", after the dashboard ran cleanly on 8081 on Rachel's Mac.
**Goal:** the dashboard defaults to a port that macOS web filtering leaves
alone. The agent chose **5580**: it sits beside the dashboard's OSC ports
(5550–5552) and away from common web or proxy ports (80, 8000, 8080, 8888)
and macOS's AirPlay ports (5000, 7000).

## Why (observed 2026-11-04 on Rachel's Mac, Python 3.9, uvicorn 0.39)

Browsers and a plain Python client on her Mac failed every WebSocket on
:8080 with 1002 "invalid opcode". The server received the HTTP upgrade request
twice, and the second copy was parsed as frames. Remote clients were fine, as
were the same dashboard on :8081, a minimal uvicorn app on :8098, and raw
loopback bytes on :8099. Not the cause: the h11 and httptools parsers,
uvloop vs asyncio, the legacy vs sans-I/O WebSocket implementations, a
system proxy, or third-party system extensions. `webfilterDNSd` (Apple
WebContentAnalysis, which Screen Time's adult-content limit turns on) was
running, and her browser sent `prefer: safe`. That makes it the likely
interceptor, but this is unconfirmed: her settings were not changed.

## Change

- `dashboard/server.py` `--port` default 5580; the two `--public-url` hints
  now print the port in use.
- `run.sh` `PORT=5580`; `dashboard/README.md` and `docs/GETTING-STARTED.md`
  show 5580.
- `tests/test_osc_transport.py`: `run.sh` and `parse_args()` both default to
  5580.

Bookmarks to :8080 stop working; `./run.sh --port 8080` still serves there.
