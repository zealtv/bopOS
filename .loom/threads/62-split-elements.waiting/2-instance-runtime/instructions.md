# 2-instance-runtime

**Status:** waiting (parent) · design gate · after `1`
**Goal:** how a split device actually runs two engines — ports, launch,
supervision, audio, and what stays node-wide.

## Collisions today

- **Ports:** 6661 and 6662 are singletons. 7770 and 8880 accept N senders but
  can't tell which instance sent.
- **One engine client** in `bopos.py` (`engine_client_lock`); readiness and
  context redelivery (`deliver_engine_context`) assume one engine.
- **Precedent:** `tools/audition.py` runs N engines with per-node
  `BOPOS_ENGINE_PORT`; `start-engine.sh` honours it only for non-Pd engines.
- **Supervision:** one `pd.pid` / `engine.pid`; `engine_alive()` checks one
  process and rides the heartbeat.
- **Audio:** no `jack_connect` anywhere; Pd auto-connects to playback 1/2, so two
  instances sum silently.

## Answer

1. **Port allocation** — derived (`6661 + slot`), allocated, or configured? How
   does a Pd patch learn its port?
2. **Launch and run context** — one `start-engine.sh` per instance, or one that
   spawns N? Which run-context values are per instance (id, groups, position,
   port, channels) vs per device (seed, run id, version, fingerprint, assets)?
   Same `BOPOS_SEED` across instances is a real choice.
3. **Audio channels** — who connects which instance to which output, and what
   happens with two stereo instances on a 2-channel card. HiFiBerry has no
   hardware mixer.
4. **Supervision** — per-instance liveness, restart, rollback; what the device
   reports when one of two is dead. The rollback path already runs full
   jackd+Pd cycles and may be behind an unexplained SSH freeze (`58`); state the
   restart story explicitly.
5. **Node-scope table** — for each of: persistence store, mute/`enabled`,
   `/os/report`, identify, hostname, patch distribution/fingerprint → node-wide,
   per-instance, or disallowed.
6. **Resources** — baseline in
   `pi-zero-performance/measurements-2026-08-13-finn-jet.md` (Zero 2 W: Pd one
   core, 81% for `bonks-pd` at 32 kHz). Say what two heavy patches on one node
   cost.

## Deliver

`proposal.md` covering the six answers. Flag anything that needs a rig
measurement rather than asserting it. Mark `.waiting`, surface to Bob.
