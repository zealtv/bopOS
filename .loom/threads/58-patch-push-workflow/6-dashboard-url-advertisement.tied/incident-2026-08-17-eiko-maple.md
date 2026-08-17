# Incident 2026-08-17 — eiko Maple would not take the `treeo` fleet patch

Live session with Bob. Dashboard on `192.168.8.223:8080`, node `eiko-maple` at
`192.168.8.141`, both at `863c787`.

## Symptom

Bob deployed the `treeo` fleet patch, repeatedly, including a whole-fleet
deploy. eiko Maple stayed on `demo-pd` and never switched. No error was noticed
in the UI.

## What was true on the node — all healthy

Nothing needed fixing on the Pi. Recorded because the diagnosis spent most of
its time here, wrongly:

* online, heartbeating, seat 2 "tenor", `device_enabled` 1, RSSI -51;
* `git_rev 863c787`, `contract_version 1.16` — current;
* engine alive, JACK up on the DigiAMP+, Pd running `demo-pd/main.pd`;
* `patches/` held only `demo-pd` and `demo-sc` — **no `treeo` directory at all**,
  and no partial staging anywhere;
* the node's journal recorded **nothing** for the failed attempts.

The node is Raspberry Pi OS (Debian, `6.18.39+rpt-rpi-v8`), not Pop!_OS as
believed at the start of the session.

## What was true on the dashboard

```
fleet_patch:  {"name": "treeo", "fingerprint": "6a7ad2b2…", "staged_at": …}
device:       patch_badge: "missing"
              fetch: {"patch:treeo": "err"}
              distribution: {}
              patches: [demo-pd, demo-sc]      # no treeo
```

`err` is set only at `osc_bridge.py:1614`, on a real `/os/fetched … err` reply
from the node. So the node **had** received a fetch request at some point and
had **failed to download the bytes** — which is the whole cause, visible in the
state the entire time and easy to read as a node fault.

## Cause

Bob was browsing the dashboard at `http://0.0.0.0:8080`. `public_url`
(`server.py:2899`) derives the node's fetch URL from the websocket's `Host`
header, and only bypasses it for loopback. `0.0.0.0` is `is_unspecified`, not
`is_loopback`, so it passed straight through and each node was told to fetch
from `http://0.0.0.0:8080/patches/treeo/.manifest.json` — an address that, on
the node, means the node itself.

## Proof

Driving `set_fleet_patch` over a websocket connected by LAN IP, so that
`public_url` derived `http://192.168.8.223:8080`, converged immediately:

```
15:26:17  OSC_OUT  /2/os/fetch  http://192.168.8.223:8080/patches/treeo/.manifest.json  patch:treeo
15:26:17  OSC_IN   /os/fetch-progress  patch:treeo queued → fetching
15:26:17  OSC_IN   /os/fetched  patch:treeo ok          # 70 ms
15:26:18  OSC_OUT  /2/os/patch  treeo
15:26:21  OSC_IN   /os/report   patch=treeo
15:26:21  DEVICE   badge: current
```

Node afterwards: `active_patch.txt` = `treeo`, `patches/treeo/` present, Pd
running `patches/treeo/main.pd` at fingerprint `6a7ad2b2…`. Total 4 s.

Nothing was changed on the node to achieve this. The only variable was the
address the dashboard was reached at.

## Two false leads, recorded so they are not re-run

**`5-fetch-tombstone-lockout`.** The row looks identical — a stale terminal
fetch record, a deploy that appears to do nothing. It is distinguishable on the
wire and only on the wire: a tombstone lockout emits **no** `/os/fetch`, this
emits one and gets `err` back. Check the OSC console first.

**`kind: "enum"` in the `treeo` manifest.** Flagged as a suspected hard-break
rejection, by analogy with the Ciro Toast and Finn Jet incidents in this same
thread. It is wrong: `enum` is a first-class kind in `python/manifest.py:20-24`
and the manifest is valid. Note that `CLAUDE.md` still says enums ship as
`options` on an integer param, which is out of date and is what prompted the
false lead.

## Gap that cost diagnosis time

Persistent journald is off on this node (`journalctl --list-boots` returns only
the current boot), so the device-side logs for the original failure were gone
before anyone looked. Same gap flagged in the 2026-08-13 update for
`5-fetch-tombstone-lockout`. `Storage=persistent` on the rig nodes remains
worth doing.
