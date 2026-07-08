# audition-1-stage0-launcher

Stage 0 of `../instructions.md`: hear a patch as N devices on one laptop.

Green light: the port spike **passed on Linux** (shared 6660 with stock PD,
SO_REUSEADDR — see `../audition-0-port-spike.waiting/results.md`). macOS is
still unverified — build Linux-first, and keep the fan-out-relay fallback
(bind 6660 once, re-send to per-instance localhost ports via startup message)
as a documented seam, not an implementation, until the macOS run answers.
**Bob (2026-07-08): Linux now, Mac later — but macOS is the likely platform
in installations and performances**, so design nothing that assumes
Linux-only socket semantics; the relay seam is load-bearing, not hypothetical.

- [ ] `tools/audition.sh` (or a simfleet mode): N × `pd -nogui -jack -jackname
      sim-pi-<n>` opening the target patch, each with its own device id via the
      start.sh `-send` startup-message mechanism. **Read start.sh, don't touch
      .pd files.**
- [ ] Jack routing: sum all instance outputs to stereo out (jack_connect
      script; spatial matrix is audition-2's job).
- [ ] **Broadcast + selector addressing only** toward instances — unicast to a
      shared port reaches exactly one process (spike finding). Heartbeats from
      instances carry uid so the dashboard distinguishes them (contract
      identity; all share the laptop IP).
- [ ] Config-compatible with simfleet so audible + protocol-only instances mix
      in one session (parent constraint).
- [ ] Cleanup that actually kills PD: `pkill -x pd` + `pkill -x pd-watchdog`
      (spike gotcha — wrapper PID isn't enough). Use bracket patterns from
      agent shells.
- [ ] Verify: launch 3 instances + dashboard, `/all/aloha` sound-check from the
      facilitator view, all three heard/logged; record the recipe here.

Done = a patch plays audibly as N devices on a Linux laptop, controlled from
the dashboard.
