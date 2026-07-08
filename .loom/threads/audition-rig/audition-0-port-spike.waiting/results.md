# Port-sharing spike — results (2026-07-08)

**Linux verdict: shared-port WORKS.** N processes on one host all receive the
same UDP broadcast on one port — with PD's stock `netreceive -u -b`, no
patches, no fan-out relay. macOS half still needs a run on Bob's Mac (below).

## Python control matrix (Linux 6.17, x86_64)

`spike_port_sharing.py`, 3 receiver processes per case:

| destination        | flags                     | bound | received      |
|--------------------|---------------------------|-------|---------------|
| broadcast          | none                      | 1/3   | rx0: 3        |
| broadcast          | SO_REUSEADDR              | 3/3   | **all see all** |
| broadcast          | SO_REUSEADDR+SO_REUSEPORT | 3/3   | **all see all** |
| unicast (loopback) | none                      | 1/3   | rx0: 3        |
| unicast (loopback) | SO_REUSEADDR              | 3/3   | one socket gets all 3 |
| unicast (loopback) | SO_REUSEADDR+SO_REUSEPORT | 3/3   | one socket gets all 3 |

- On Linux, **SO_REUSEADDR alone is enough** for shared bind + broadcast
  delivery to every socket. SO_REUSEPORT changes nothing for broadcast.
- **Unicast to a shared port reaches exactly one process** (last-bound with
  REUSEADDR; kernel-hashed with REUSEPORT). Direct consequence for the
  audition rig: anything the dashboard unicasts to a node IP (e.g. `/os/*`
  replies land fine — they *originate* per-instance — but *requests* sent
  unicast to the shared host reach one arbitrary instance). The contract's
  broadcast-with-uid/id-selector pattern (`/all/os/...`, `/<id>/...`) is the
  right addressing for audible instances; per-instance helper features that
  assume "one node = one IP" are not.

## PD (`netreceive -u -b 6660`, real `pd/bopos.osc.pd`, pd on /usr/local/bin)

- Two (later four — see below) headless instances opened the deployed patch:
  **zero bind errors**; PD sets SO_REUSEADDR on UDP receive sockets on Linux.
- One broadcast `/-1/aloha 1` produced **one aloha reply per running
  instance** (4 instances → 4 replies from 4 distinct source ports). Both
  reception *and* application confirmed, end-to-end through the real patch.
- Bonus finding: `/all/aloha` makes this legacy patch print
  `error: couldn't convert all to float` and NOT fire — PD-side legacy
  routing only matches numeric selectors (`/-1/`, `/3/`). The deployed-fleet
  `all` handling comes from helper.py's contract listener, not from
  bopos.osc.pd. (Both instances printed the error, which is itself reception
  evidence.) Noted for the §13 migration record; today's dashboards send
  `/all/aloha` and the *PD* side ignores it silently on legacy nodes.
- `spike_pd.sh` gotcha it exposed: killing the `pd` wrapper PID doesn't kill
  the actual `pd` process (watchdog respawn/fork) — the first run's instances
  were still alive during the second run. Clean up with `pkill -x pd` +
  `pkill -x pd-watchdog`.

## macOS — for Bob (the composition machine)

BSD socket semantics differ (shared UDP bind classically wants SO_REUSEPORT,
which Python sets but PD may not). One command from the repo root:

```sh
python3 .loom/threads/audition-rig/audition-0-port-spike.waiting/spike_port_sharing.py \
  && bash .loom/threads/audition-rig/audition-0-port-spike.waiting/spike_pd.sh /tmp
```

Read: the broadcast rows should say ALL SEE ALL, and the PD run should show
no bind errors + an aloha reply per instance. If PD fails to share on macOS,
the cheapest fallback stays the tiny UDP fan-out relay (bind 6660 once,
re-send to per-instance localhost ports passed via startup message).

## Verdict for the parent (audition-rig)

Shared-port works on Linux with stock PD — Stage A can assume N engine
instances on one Linux laptop hear the same 6660 broadcasts. Keep unicast
out of the audible-instance path (broadcast + selector only). macOS pending.
