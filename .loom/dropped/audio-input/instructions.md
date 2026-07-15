# audio-input

**Goal:** bopOS supports audio capture where the hardware provides it. Today jackd is
launched playback-only (`start.sh` line ~78, `-P` flag) with `SOUNDCARD` hardcoded, and
the usual DigiAmp+ boards have no input anyway (review §3.7, §4).

Checklist:
- [ ] Move soundcard + jack parameters into `bopos.config`: `SOUNDCARD`, sample rate,
      period/buffers, and a `CAPTURE on|off` (drops the `-P` playback-only flag and sets
      channel counts) — long-standing TODO, also unblocks per-patch audio configs
- [ ] Verify capture end-to-end on at least one input-capable HAT; document the recipe
- [ ] Hardware guidance in docs: which HATs give line/mic in (e.g. HiFiBerry DAC+ ADC,
      IQaudio Codec Zero, USB interfaces as fallback) vs the out-only DigiAmp+
- [ ] Contract note: how a patch discovers whether input channels exist

This is part hardware selection, part config plumbing — the config plumbing is the bopOS
work; the HAT choice is per-project.
