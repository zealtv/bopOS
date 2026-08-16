# 2-instance-runtime

How a split device actually runs two engines: ports, launch, supervision,
audio, and what stays node-scope.

Design gate, downstream of `1-split-identity-model`'s ruling on the unit.
Do not implement past it.

## Starting state — the collisions, measured

- **Ports.** 6661 bopos→engine and 6662 io→engine are single localhost
  singletons (`docs/PORTS.md`); two instances collide on both immediately.
  7770 (engine→bopos) and 8880 (engine→io) are listeners so they survive N
  senders, but neither carries any way to say *which* instance sent.
- **`bopos.py` holds one engine client.** `OSCServer(('', 7770))` and one
  `OSCClient` connected to `127.0.0.1:6661` behind `engine_client_lock`
  (`:55-58`); every `send_to_engine` in the file goes down it, and its
  connection-refused swallowing plus `deliver_engine_context` redelivery
  (`:741`) is the node's whole engine-readiness model. Under split there are
  N ports, N readiness states, and N redeliveries.
- **The precedent exists.** `tools/audition.py` runs N engines on one machine
  with `--engine-port-base 16661` and per-node `BOPOS_ENGINE_PORT`
  (`:143`, `:178`, `:265`, `:325`), and `bash/start-engine.sh` already honours
  `BOPOS_ENGINE_PORT` for the non-PD branch. **Pure Data does not read it** —
  the PD branch hardcodes the patch's own port binding. Say what changes.
- **Supervision is single.** `start-engine.sh` writes one `pd.pid` /
  `engine.pid` / `engine.name`; `engine_alive()` (`:313`) checks one process
  plus JACK, and its boolean rides the heartbeat. Split needs a per-instance
  answer and a rule for what the device reports when one of two is dead.
- **Audio has no mechanism at all.** Nothing calls `jack_connect` anywhere;
  `pd -nogui -jack` auto-connects to `system:playback_1/2`, so two instances
  would sum onto the same pair silently. Today the *patch* maps element →
  channel; split takes that away and gives it to nobody.

## What must be answered

1. **Port allocation.** Derived from slot index (`6661 + slot`,
   `6662 + slot`), allocated, or configured? Say how a patch learns its own
   port — the PD branch currently cannot be told one.
2. **Launch and run context.** One `start-engine.sh` invocation per instance,
   or one that spawns N? Which run-context values are per instance (id, groups,
   element position, engine port, audio channels) and which stay per device
   (seed, run id, version, patch fingerprint, assets — note `BOPOS_SEED`
   identical across instances may or may not be wanted, and that is a real
   choice).
3. **Audio channel assignment.** Who connects an instance's outputs to which
   `system:playback_*`, and what happens on a 2-channel card with two stereo
   instances. This is the piece with no prior art in the repo; treat the
   HiFiBerry finding in CLAUDE.md (no hardware mixer, volume entirely
   software) as a constraint.
4. **Supervision and reporting.** Per-instance liveness, restart, and rollback.
   `bopos.py`'s patch-switch rollback path (`:1858-1877`) already runs full
   jackd+Pd cycles and is implicated in the unexplained SSH freeze noted in
   `58`; doubling engines doubles that cost, so state the restart story
   explicitly rather than inheriting it.
5. **What stays node-scope, and what a shared thing does with two writers.**
   Named explicitly: the persistence store (`store`/`load` on 7770, flat key
   namespace, `python/store.py` — two instances share a keyspace today),
   mute/`enabled` (`enforce_mute` `:571`, `set_device_enabled` `:604`, ALSA
   device-wide), `/os/report`, `identify`, hostname, patch distribution and
   fingerprint. For each: node-scope, per-instance, or disallowed.
6. **Resource envelope.** State what two engines cost on the real hardware.
   `pi-zero-performance/measurements-2026-08-13-finn-jet.md` has the baseline:
   Pd 51% of a core on `demo-pd`, 99% on `bonks-pd`, single-threaded, three of
   four cores unusable. Split is the only shape that uses them — but the
   proposal should say what happens when two `bonks-pd`-class patches land on
   one node, not just that headroom exists.

## Deliver

`proposal.md`: port model, launch and supervision model, the audio channel
ruling, the node-scope table, and the resource statement. Flag anything that
needs a rig measurement rather than a judgement — do not claim hardware
behaviour that has not been measured.

Then mark `.waiting` and surface it.
