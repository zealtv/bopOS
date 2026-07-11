# Port-sharing spike — results (2026-07-08)

**Verdict: shared-port works on Linux, but stock PD needs fan-out on macOS.**
Linux delivers one broadcast to every stock `netreceive -u -b` instance on
port 6660. macOS can do the same with Python sockets only when
`SO_REUSEPORT` is set; stock PD 0.55.2 does not make its UDP receivers
shareable there, so the second instance cannot bind.

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

## macOS result (composition machine, 2026-07-11)

Environment:

- macOS 14.6.1 (23G93), arm64
- Python 3.14.4
- Pure Data 0.55.2, universal arm64/x86_64 binary at
  `/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd`

Commands run from the repository root:

```sh
python3 .loom/threads/audition-rig/audition-0-port-spike.stitching/spike_port_sharing.py
PD='/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd' \
  bash .loom/threads/audition-rig/audition-0-port-spike.stitching/spike_pd.sh /tmp
```

Python control result:

- no flags or `SO_REUSEADDR` alone: only 1/3 receivers bind;
- `SO_REUSEADDR+SO_REUSEPORT`: 3/3 bind and every broadcast receiver gets
  all three datagrams; and
- shared-port unicast reaches only one of the three receivers.

The exact matrix is retained in `mac-python-output.txt`.

PD result:

- both headless instances start and emit their three load-time reports from
  distinct source ports;
- the second instance reports three `netreceive: listen failed: Address
  already in use (48)` errors, including the command port bind;
- the first instance receives `/all/aloha` but the legacy patch rejects the
  string selector with `couldn't convert all to float`; and
- after the harness exits, `pgrep` finds no `pd`, `pd-watchdog`, or app-bundle
  PD processes. No manual cleanup was required on this run.

The Mac logs are retained as `mac-pd-a.log`, `mac-pd-b.log`, and
`mac-replies.log`. The six captured datagrams are startup evidence, not proof
that both instances received the later broadcast.

## Verdict for the parent (audition-rig)

Shared-port works on Linux with stock PD. On macOS, Stage 0 needs a relay that
owns broadcast port 6660 and delivers to distinct per-instance localhost engine
ports. Keep unicast out of the audible-instance LAN path on both platforms;
use broadcast plus selectors.

This should align with, and generalize, the helper-to-SuperCollider affordance
proved by `seam-5`: one LAN listener matches a node selector, strips it, and
delivers an engine-local surface. The existing implementation is not directly
reusable for the audition rig because it models one node, targets fixed port
6661, and deliberately excludes PD. Stage 0 should evaluate one engine-neutral
audition relay with N virtual-node identities and N local ports rather than a
PD-only datagram duplicator. Multiple SC audition instances benefit too because
they would otherwise contend for fixed port 6661.

The remaining PD boundary is whether its engine receiver can select a local
port through the existing startup-message mechanism. If not, that receiver
change is Bob-owned `.pd` work and must be recorded rather than implemented by
an agent. Per the spike brief, the relay itself belongs to Stage 0, not here.
