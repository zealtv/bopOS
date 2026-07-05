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
- [ ] Engine track — **SuperCollider is under serious consideration on its own merits**
      (review §11), not just as a CPU fallback: scsynth is OSC-native, headless,
      multi-core-friendlier, and **more agent-friendly than PD** — and agent-coded
      composition is a target workflow. bop/PD remains the hand-patched artist layer;
      Kite Choir-scale work will probably prefer SC. Deliverable: a proof-of-concept SC
      patch running as a bopOS patch (entrypoint via its own start.sh) on the Zero,
      with a CPU comparison vs an equivalent PD patch. RNBO noted as future-only
      (its runner competes with bopOS process management). Also glance at
      Faust-compiled natives / Csound for completeness.

Done when: documented Zero 2 W defaults committed, with the measurement showing the
headroom gained, and a short written verdict on whether a non-PD engine is warranted.
