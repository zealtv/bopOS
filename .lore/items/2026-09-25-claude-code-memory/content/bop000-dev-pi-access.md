---
name: bop000-dev-pi-access
description: How to reach the bop000 dev Pi (DigiAMP+) for hardware verification
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5d1434cd-f8d1-41db-af2f-fa4e7a52b891
  modified: 2026-07-23T06:08:39.907Z
---

**2026-08-14:** **192.168.0.102 is now `finn-jet`** (Pi 5-class, Debian
kernel 6.18, `~/venv` Python 3.13.5, soundcard `DigiAMP`, uid
`2c:cf:67:b3:0a:58`, Seat 0) — the "new-bop" identity below is stale for that
address. My key is **not** installed there: `ssh pi@finn-jet.local` asks for a
password. Bob offers an authenticated shell in a **tmux pane beside the Claude
pane** instead — find it with `tmux list-panes -a` (it was `0:1.2`, title
`ssh`) and drive it with `tmux send-keys` + `tmux capture-pane -p`, echoing a
unique marker to know when a command finished. `bash/restart.sh` `sudo`s and so
needs Bob; `bash/stop.sh` + `bash/start.sh` run fine as `pi`, which is the way
to restart the stack unattended.

**2026-07-23:** a *fresh-install* dev Pi is up as `new-bop` at **192.168.0.102**
(aarch64, `~/bopOS` checkout, `python/bopos.py`, no `bopos.service` yet). My
spectre pubkey was added to its `authorized_keys` via Bob's live tmux pane, so
`ssh -i ~/.ssh/id_ed25519_spectre pi@192.168.0.102` now works direct/BatchMode.
Bob's authenticated console for this Pi lives in local tmux session `0` pane
`0:0.0` (drive with `tmux send-keys -t 0 … Enter` for sudo he must approve).
This freshly-flashed node is the intended repro rig for the node-install bug
(thread `29-fleet-patch-sync-hang`).

Dev Pi `bop000` (DigiAMP+, Debian 13/Trixie): ssh works with
`ssh -i ~/.ssh/id_ed25519_spectre pi@192.168.0.101` (confirmed 2026-07-12;
IP may change on DHCP — `bop000.local` resolves via mDNS but key auth is per
that identity file, not the default agent). `sudo` prompts for a password Bob
must type. bopOS lives at `~/bopOS`; helper runs under systemd unit
`bopos-helper`. A stash `bop000 bench edits pre-boundary-5` and a
`systemd.local-copy/` dir were left on the Pi 2026-07-12 after reconciling
local bench edits with main.

bop000 is a **Pi Zero 2 W** (quad A53, 415MB RAM), soundcard `DigiAMP`. Bob
sometimes offers a tmux pane with a session on it for commands needing his
authentication (sudo) — confirm the pane in-session, don't assume one
exists. Normal idle state: only `bopos.py`
running, audio stack down (`bash/start-engine.sh` starts it). Perf baseline
2026-07-13 (`.loom/tied/zero-0-measure-kit/`): 0 xruns across the whole jackd
grid, big headroom at production settings.

Related: [[samples-thread-needs-dialogue]], [[bopos-single-object-idea]].
