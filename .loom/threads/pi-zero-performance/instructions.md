# pi-zero-performance

**Goal:** enough CPU headroom on the Pi Zero 2 W for real patches. Bob is seeing CPU
overhead, likely PD single-threaded (review §3.1). **Overlaps kite-choir-brains loom
`bopos-uptodate/pi-zero-optimisation`** — the spool-specific tuning lives there; the
generic bopOS defaults and the engine survey live here.

Measure first, then tune:
- [ ] A repeatable measurement: xrun count + `top`/`vcgencmd measure_temp` under a
      reference patch; record baseline before changing anything
- [ ] jackd tuning matrix: `-p` (512→1024), `-n` (2→3), 44.1k vs 22.05k (a commented
      22.05k line already exists in start.sh); commit Zero-safe defaults
- [ ] PD cost levers: `-rt` scheduling, strip `bop.ui` GUI abstractions on-target,
      io poll rate (10 Hz default) vs patch needs
- [ ] Process split: check helper.py / io bridge nice levels; they should never steal
      from the audio thread
- [ ] Engine survey (only if PD can't hold real-time for target patch complexity):
      SuperCollider (scsynth headless is the obvious candidate — multi-core-friendlier,
      OSC-native so it fits the contract), plus a quick look at alternatives
      (Faust-compiled natives, Csound). The `osc-schema-contract` entrypoint
      generalisation is what makes an engine swap a patch-level choice, not a fork.

Done when: documented Zero 2 W defaults committed, with the measurement showing the
headroom gained, and a short written verdict on whether a non-PD engine is warranted.
