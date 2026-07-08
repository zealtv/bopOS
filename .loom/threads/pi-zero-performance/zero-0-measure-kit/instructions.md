# zero-0-measure-kit

The measurement half (agent-doable): a repeatable performance measurement kit
so tuning (zero-1, hardware) is a fill-in-the-table exercise.

- [ ] `tools/perf_measure.sh` (or .py): capture xrun count (jackd log or
      jack_xrun hook), CPU per process (pd/helper.py/io bridge), temp
      (`vcgencmd measure_temp`, absent gracefully on non-Pi), over a timed run
      with a named patch; emit one comparable report line/file per run.
- [ ] The tuning matrix *script*: iterate jackd `-p`/`-n`/rate combos ×
      reference patch, one report per cell — ready for Bob to run on a Zero
      (zero-1). Include the commented 22.05k start.sh option as a cell.
- [ ] Check & document helper.py / io bridge nice levels as found (fixes only
      if trivially safe; PD `-rt` observations belong in the doc, changes to
      start.sh flags are zero-1's hardware-verified call).
- [ ] Smoke-test the kit on the laptop rig (`bash/start-laptop.sh`) or a local
      pd -jack instance; commit a sample report here.
- [ ] Doc: how to run it, what the columns mean, where baselines get recorded.

Cross-repo: spool-specific tuning lives in `kite-choir-brains`
`bopos-uptodate/pi-zero-optimisation` — generic kit here, coordinate don't
duplicate.
