# The Finn Jet / Ciro Toast rig

When hardware verification is needed, the two-device rig is Finn Jet (fleet node) and Ciro Toast (standalone); `bop000` is a spare Zero 2 W.

- Finn Jet: Pi Zero 2 W, IQaudIO DigiAMP+, runs 32000/1024/2 locally (repo default stays 44100). LIS3DH on the I2C bus.
- Ciro Toast: HiFiBerry DAC, ADS1115 at `0x4b`.
- HiFiBerry boards have no hardware mixer — `amixer` warnings at startup are normal; volume is software.
- Persistent journald is off on these nodes, so logs from a previous boot are gone; the io bridge and node services now log to a capped file.
- Pd's audio is single-threaded; see `.loom/threads/pi-zero-performance/measurements-2026-08-13-finn-jet.md`.
- Finn Jet is a kite spool — the fleet-node case. Ciro Toast is being set up to run standalone.

## Access

IPs are DHCP; confirm in-session.

- **Finn Jet** (was `192.168.0.102`, `finn-jet.local`): the agent key is **not** installed. Bob offers an authenticated shell in a tmux pane beside Claude's — find it with `tmux list-panes -a`, drive it with `tmux send-keys` + `tmux capture-pane -p`, and echo a unique marker to know when a command finished.
- **bop000** (was `192.168.0.101`, `bop000.local`): `ssh -i ~/.ssh/id_ed25519_spectre pi@<host>`. Zero 2 W + DigiAMP+, Debian 13.
- `sudo` needs Bob (so does `bash/restart.sh`). `bash/stop.sh` then `bash/start.sh` restarts the stack as `pi`; `bash/stop-engine.sh` + `bash/start-engine.sh` re-reads `bopos.config` without a reboot.

## Also

- The Pi dev loop (push → pull on Pi, stop/restart sequence) is in kite-choir-brains' `bopos-dev` skill.

## Triggers

- Finn Jet
- Ciro Toast
- bop000
- HiFiBerry
- DigiAMP

## Associations

- [[hardware-claims]]
