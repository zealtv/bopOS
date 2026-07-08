# input-0-config-plumbing

The bopOS half of audio input: config plumbing (parent has context; hardware
recipe is input-1).

- [ ] Move soundcard + jack parameters into `bopos.config`: `SOUNDCARD`,
      sample rate, period/buffers, `CAPTURE on|off` (CAPTURE on drops jackd's
      `-P` playback-only flag and sets channel counts). start.sh reads them;
      current hardcoded values become the defaults — a Pi with an old config
      must behave identically.
- [ ] Contract note (additive): how a patch discovers whether input channels
      exist — likely a manifest/`/os/report` field; shape it, record it in
      docs/OSC-CONTRACT.md, and add it to simfleet if it's on the wire.
- [ ] Verify on the laptop rig (`bash/start-laptop.sh`) or a local jackd:
      CAPTURE off reproduces today's launch exactly (diff the jackd command
      line); CAPTURE on launches with capture channels where the device has
      them. Record commands + output here.

Real-HAT verification is input-1 (.waiting) — don't claim it.
Coordinates with zero-1: both touch jackd parameters in start.sh/config —
whoever lands second rebases on the first's shape.
