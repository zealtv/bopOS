# Performance measurement kit

Repeatable measurement of a node's audio stack, so jackd tuning on real
hardware (`pi-zero-performance`) is a fill-in-the-table exercise rather than
an anecdote. Two tools, both dependency-free:

- `tools/perf_measure.py` — one timed measurement of whatever is running.
- `tools/perf_matrix.sh` — sweeps jackd settings × the active patch and runs
  one measurement per cell.

## One measurement

With the stack already running (any way it got started):

```
python3 tools/perf_measure.py run --duration 60 --label baseline \
    --patch default --out reports.jsonl
```

Add `--jack-log <file>` if jackd's stderr is going to a file — xruns are
counted from lines appended to it during the window. Without it the `xruns`
column is `-` (unknown, *not* zero). Reports append to `--out` as JSON lines;
render any collection of them with:

```
python3 tools/perf_measure.py summarize reports.jsonl
```

## The tuning matrix

```
tools/perf_matrix.sh              # default grid, 60s per cell
tools/perf_matrix.sh -d 30 -c "44100:512:2 48000:512:2"
```

Cells are `rate:period:nperiods`. The default grid brackets the production
`bash/start-engine.sh` line (`44100:512:2`) and includes the commented 22.05k
option from start.sh (`22050:1024:2`). Flags other than `-r/-p/-n` match
start-engine.sh exactly (`-P70 -p16 -t2000 -s -P`, alsa, `DigiAMP` unless
`-s`/`$SOUNDCARD` says otherwise).

The script **takes over the audio device**: it stops any running engine and
jackd first (`bopos.py` and the io bridge stay up, so the measurement includes
their production background load), runs each cell with the active patch, and
leaves the stack stopped — restart with `bash/start-engine.sh`. Per-cell
jackd/pd logs land next to `report.jsonl` in the output directory
(default `run/perf-<timestamp>/`).

The patch runs unattended, so cells measure the patch's autonomous load. If a
patch is silent until driven, drive it (dashboard, `tools/simfleet.py`, or a
cue) during the window and say so in `--notes` / the baseline record.

## Columns

| column | meaning |
|---|---|
| `xruns` | xrun mentions appended to the jackd log during the window; `-` = no log available |
| `dsp%` | JACK DSP load mean/max (via `jack_cpu_load`), `-` if the tool is absent |
| `jackd%` `pd%` `bopos%` | per-process CPU mean/max over the window (100 = one core) |
| `temp°C` | SoC temp start→max (`vcgencmd`, sysfs fallback; `-` off-Pi) |
| `load1` | 1-minute load average at the end of the run |

A cell is *usable* when xruns stay at 0 for a full-length run at realistic
patch load with headroom on `dsp%`/`pd%`; watch `temp°C` on enclosed Zeros —
throttling starts near 80 °C and shows up as late-run xruns.

## Baselines

Recorded baselines live with the loom stitch that produced them
(`.loom/**/zero-*/`), which travels into `tied/`. The first sample report from
the bop000 Zero 2 W smoke test lives in the `zero-0-measure-kit` stitch.

## Scheduling as found (bop000, 2026-07-13)

- `jackd` runs with `-P70` (SCHED_FIFO 70) and `-p16`; realtime comes from the
  `audio` group rlimits, no sudo involved.
- `bopos.py` and `io/main.py` run at nice 0, no realtime — fine: they are
  control-plane, and their CPU shows up in the report if they ever misbehave.
- PD is launched without `-rt`; on a busy Zero, PD competing at nice 0 with
  everything else is a plausible xrun source. Whether to add `-rt` (needs the
  same audio-group rlimits) is a hardware-verified call for `zero-1`, not a
  default to flip here.
