# zero-0-measure-kit — verification record (2026-07-13)

Deliverables: `tools/perf_measure.py`, `tools/perf_matrix.sh`, `docs/PERF.md`
(commits `ffee4a7`, `4d6f76a`).

## Smoke test — real Pi Zero 2 W (bop000), not the laptop rig

Bob had bop000 (Zero 2 W, DigiAMP+, Pi OS Trixie arm64) up for this session,
so the smoke test ran on the actual target hardware instead of the laptop
rig. `bopos.py` stayed running throughout (production-like background);
matrix took over the audio device and left the stack stopped, as documented.

Commands (on bop000):

```
tools/perf_matrix.sh -d 30 -o run/perf-smoke -c "44100:512:2 22050:1024:2"
tools/perf_matrix.sh -d 20 -o run/perf-smoke2 -c "44100:512:2"   # dsp% fix check
tools/perf_matrix.sh -d 60 -o run/perf-baseline-20260713         # full grid
```

Sample reports are in `baseline-bop000-20260713.jsonl` next to this file;
render with `python3 tools/perf_measure.py summarize <file>`.

## Findings — full default grid, 60s/cell (bop000, open air, idle patch)

```
     label       xruns   dsp%      jackd%     pd%        bopos%   temp°C     load1
r44100-p512-n2   0       1.2/1.4   1.3/4.0    51.3/52.8  1.3/1.5  36.5→37.6  0.06
r44100-p256-n2   0       1.8/2.3   1.9/3.5    52.9/54.3  1.3/2.0  37.6→38.6  0.75
r44100-p1024-n2  0       0.8/0.8   0.8/2.5    50.7/52.4  1.2/2.0  38.1→38.6  0.46
r44100-p512-n3   0       1.2/1.3   1.3/3.5    51.5/52.9  1.3/2.0  38.6→39.2  0.16
r22050-p1024-n2  0       0.5/0.5   0.6/3.0    33.9/35.9  1.6/2.2  37.6→38.1  0.20
```

- **0 xruns in every cell**, including the tight 256-frame period. The
  production settings (44.1k/512/2) have ample headroom with the default
  patch idling: pd ≈ 51% of one core, DSP ≈ 1.2%, temp under 40 °C.
- The commented 22.05k option drops pd to ≈ 34% — real headroom in reserve,
  but not needed at this load.
- Caveat for zero-1: idle default patch, open-air board. Enclosure heat and a
  driven/heavier patch are exactly what the zero-1 matrix should sweep.
- Nice levels as found: jackd SCHED_FIFO 70 (`-P70`), bopos.py / io bridge /
  pd all nice 0, pd without `-rt`. Nothing trivially-safe to fix; `-rt` is
  zero-1's hardware-verified call. Documented in `docs/PERF.md`.
- `jack_cpu_load` block-buffers when piped — the watcher drains it after
  termination (commit `4d6f76a`), otherwise `dsp%` silently reads empty.

## Checklist vs instructions

- [x] `perf_measure.py` — timed run, per-proc CPU, temp (graceful off-Pi:
      mac dry-run exercised the `ps` fallback), xruns from jackd log, one
      comparable JSON line per run + `summarize` table mode.
- [x] Tuning matrix script — default grid brackets production and includes
      the 22.05k start.sh cell; per-cell jackd/pd logs retained.
- [x] Nice levels checked & documented as found; no changes made.
- [x] Smoke test + sample report committed here (real Zero, better than the
      laptop-rig minimum the instructions asked for).
- [x] Doc: `docs/PERF.md`.

Cross-repo note: this is the generic kit; spool-specific tuning stays in
`kite-choir-brains` `bopos-uptodate/pi-zero-optimisation`.
