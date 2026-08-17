# Verification — 6-dashboard-url-advertisement

## Software gate — passed

`tests/test_osc_transport.py`, browser-free, in `fast`.

* `DistributionUrlRoutingTests` gains five cases pinning `public_url` against
  `0.0.0.0`, `::`, `127.0.0.1`, a LAN literal, a non-IP hostname, and the
  no-route error naming `--public-url`.
* Failure verified against the unfixed tree: reverting the one condition to
  `is_loopback` alone fails 3 of 6 with `- http://0.0.0.0:8080` /
  `- http://[::]:8080` against the expected derived address.
* `RunScriptUrlBannerTests` pins the `run.sh` half in source: `--port` reaches
  the printed URL in both spellings, and the bind address is never advertised.

`tools/run-tests.sh fast` — **363 tests, OK.**

## `run.sh` shell assertion — passed

Run with a stub venv python that echoes its arguments, and a stub `ifconfig`
for the single/no-address branches:

* default: lists both of this machine's addresses, RFC1918 first, no pick;
  execs with `--host 0.0.0.0`.
* `--port 9000` and `--port=9100`: every printed URL carries the port, and the
  argument still reaches the server verbatim.
* one address: `==> Dashboard on http://192.168.8.223:8080/`.
* no address: `localhost` fallback plus the `--public-url` pointer.
* `0.0.0.0` never appears as an address to open, only in the "do not open" line.

## Hardware gate — NOT RUN, and not claimed

The healthy path is already discharged (eiko Maple converged in 4 s once the
fetch URL was `http://192.168.8.223:8080` — see the incident note). **The fix
itself has not been observed on hardware**: a dashboard browsed at
`0.0.0.0:8080` handing a node a derived URL and the node fetching successfully
has only been shown as a unit test. No rig was available this session. Anyone
with the rig should do exactly that one thing: open the dashboard at
`http://0.0.0.0:8080`, deploy a fleet patch, and confirm `/os/fetch` carries a
LAN address and comes back `ok`.
