# Soak stimulus + analysis tooling

Companions to `tools/i2c_soak.py`, built 2026-08-15 for the Kite Choir spool-pole I2C validation.
They exist to answer an interference question **without an 8-hour overnight run at max volume** —
the rig lives in an apartment, and the pass criterion is per-transaction, not per-hour.

## The method

1. **Compress time with polling rate.** `i2c_soak.py run --interval 0` free-runs at ~593 txn/s
   (100 kHz) or ~1,574 (400 kHz) against the bridge's production 10 Hz — a **59–157× compression**.
   A 20-minute run carries ~19.7 h of production-rate polling. It also errs conservative: a busier
   bus has more chances to coincide with an interferer transient than the real one will.
   ⚠️ **Always pass `--interval 0` when comparing rates** — the default is 0.02 s (50 Hz), and
   forgetting it looks exactly like a throughput collapse.
2. **Pair the stimulus instead of extending it.** Alternate 30 s stressor / 30 s silence aligned to
   `--bucket 30`. The **difference between loud and quiet buckets is the interferer** — more
   sensitive than a pass/fail total, and it halves the loud time.
3. **Report the bound, not "zero".** 0 failures in *n* trials → 95% upper bound of **3/n**.

## Usage

```sh
# build the stressor (kind, seconds, outfile, dBFS)
python3 make_stressor.py gated-noise 30 gated-noise.wav -6

# start the soak, then the paired driver alongside it
i2c_soak.py run --label C1-paired --interval 0 --bucket 30 --duration 1200 --out c1.jsonl &
./paired.sh 20

# classify buckets by wall clock and compare
python3 pairedstats.py <soak-start-ts-file> audio-schedule.txt c1.jsonl
```

Stop the autostart stack's bridge first (`io/main.py` polls at 10 Hz and contends), and stop
`pd`/`jackd` if `aplay` needs the card.

## Choosing a stressor

Coupling follows **dV/dt and dI/dt**, so **crest factor beats loudness** — music is the *easy* case
at a given peak level. `gated-noise` is nastier than programme material *and* quieter, because the
8 Hz hard gate adds supply-current steps a steady signal never produces.

⚠️ `gated-square` is band-limited to ~8 kHz on purpose. A full-scale square into a passive 2-way will
cook the tweeter, and the amp's output LC filter limits the real slew anyway.

`sweep` is a **diagnostic**, not a screen — run it only if something errors, to find the coupling
frequency by correlating against bucket timestamps.
