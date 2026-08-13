# Finn Jet CPU measurements — 2026-08-13

Supporting material, not a claim that any checklist item is done. Collected in
a session that started as a patch-switching bug (`58/5`) and turned into
profiling when Bob noticed `bonks-pd` stuttering after the patch was updated.
Bob is doing targeted profiling in a later session; this is the baseline he
should not have to re-measure.

Node: Finn Jet, Pi Zero 2 W (4 cores), 415 MB RAM, IQaudIO DigiAMP+.
Framework at `96bec64`/`19471a8`. JACK 44100 / period 512 / nperiods 2, all
node defaults from `bopos.config`. Not thermally throttled at any point
(`vcgencmd get_throttled` = `0x0`, 46.2 °C).

## The io bridge is not a CPU cost on this node

| process | CPU | note |
|---|---|---|
| `python/io/main.py` | **0.1%** | cumulative over 47 min |
| `jackd` | 1.1% | |
| `pd` (bonks-pd) | **99%** | one full core |

Poll rate 10 Hz, and **no peripherals are configured** — there is no
`python/io/config.json` on this device, so the loop reads nothing. This was
checked because Bob suspected `3919cb2` (ADS1115 at 860 SPS, sleep-remainder
poll timing). That change is exonerated *on this node*; it says nothing about
a node with peripherals actually attached, which is the case the goal's "io
poll rate (10 Hz default) vs patch needs" item is really about.

## Pd cost is patch-dependent, and the audio thread is not where it goes

Same node, same JACK settings, A/B'd by switching patches:

| patch | Pd CPU |
|---|---|
| `demo-pd` | **51%** of one core |
| `bonks-pd` | **99%** of one core (measured 3×) |

Per-thread, under `bonks-pd`: the **main Pd thread** took ~205 ticks / 2 s
while the **JACK client thread took 1 tick / 2 s**. Pd runs DSP in its own
scheduler thread in polling mode, so this is DSP plus scheduler, not a runaway
message loop — the patch's only `metro` is `metro 1000`.

Consequence, confirmed in the engine log:

```
JackEngine::XRun: client = pure_data was not finished, state = Triggered
```

Note the ceiling: three of four cores sit idle and cannot help, because Pd's
audio path is single-threaded. This is the review §3.1 suspicion, measured.

## `-callback` was tried and is WORSE — do not re-run this experiment

Hypothesis: Pd's default is polling mode (`pd -help`: `-nocallback -- use
polling-mode (true by default)`), so the 51% floor under a small demo patch
looked like fixed spin overhead that `-callback` would remove.

**Refuted, twice over.** `PD_CALLBACK=1` was implemented, deployed to Finn Jet
and measured:

| mode | Pd CPU | xruns |
|---|---|---|
| polling (default) | 98% | ~2 in 3 min |
| callback | **100%** | **518 XRun lines** in the same engine log |

Bob, listening live: *"sounds worse"* — arriving independently of the log.
Callback mode does not reduce CPU at all and destroys scheduling. The flag was
reverted (`19471a8`, reverted by `1cec78e`); the device is back on polling with
0 xruns.

So the 51% floor is **not** polling overhead, and remains unexplained. That is
the open question, and it is a better lead than the tuning matrix: whatever
costs 51% on a nearly-empty patch is being paid by every patch on every node.

## What was NOT established

- **Why `bonks-pd` stutters now when it did not before.** The likeliest cause
  is that the patch itself changed: this session delivered the current host
  `main.pd` (11406 bytes) over the device's 2026-07-25 copy (11554 bytes), and
  the last time it ran on Finn Jet was necessarily before 2026-07-28, when the
  manifest grammar break made that copy unstartable. **The old bytes are
  overwritten and `patches/` is gitignored, so no diff is possible** from
  anywhere reachable. Hypothesis, not a finding.
- **The 51% floor**, per above.
- **The buffer-size lever.** Raising period 512 → 1024 is untried and is the
  obvious cheap next move; it is already the goal's second checklist item.
- **The SSH freeze** Bob saw during a failed patch switch (see the
  2026-08-13 CLAUDE.md update). Not reproduced. Persistent journald is off on
  this node, so only the current boot is retained. **Turning on
  `Storage=persistent` before the next profiling session** would make it
  diagnosable, and is worth doing on every rig node.

## Method notes for whoever profiles next

- CPU was read as `/proc/<pid>/stat` fields 14+15 sampled across a known
  interval, not from `top`'s instantaneous column, and per-thread from
  `/proc/<pid>/task/*/stat`. The per-thread split is what separated "DSP is
  expensive" from "something is spinning", and is the measurement worth
  repeating first.
- `jack_cpu_load` runs continuously and will hang a non-interactive shell;
  `timeout` it or avoid it.
- Restarting the engine by hand is `bash bash/stop-engine.sh` then
  `nohup bash bash/start-engine.sh`, which is enough to re-read `bopos.config`
  without a patch switch or reboot.

---

# Follow-up, same day: 22.05 kHz removes the stutter

Bob's own change, measured afterwards. Node now at **22050 / 1024 / 2**
(both rate and period changed; Bob reports **1024 alone at 44.1k made no
audible difference**, so the sample rate is the lever).

| metric | 44.1k / 512 | 22.05k / 1024 |
|---|---|---|
| `pd` | 99% of a core | **57%** |
| xruns | ~2 in 3 min | **1 in 10 min** |
| JACK client thread | ~0.2% | 0 ticks in 4 s |
| `jackd` | 1.1% | 0.6% |
| `io/main.py` | 0.1% | 0.1% |
| system total | ~25% of 4 cores | 14.6% |

45.1 °C, `throttled=0x0`.

## This partly retires the "51% floor" open question

Two points on the same patch separate fixed cost from DSP cost. If halving the
rate halves only the DSP term:

- `bonks-pd`: 99% @ 44.1k, 57% @ 22.05k  ->  **fixed ~15%, DSP ~84%** @ 44.1k
- `demo-pd`: 51% @ 44.1k  ->  **DSP ~36%** @ 44.1k

So the floor recorded above as "unexplained and paid by every patch on every
node" is mostly **real DSP in demo-pd**, with only ~15% fixed. `demo-pd` is not
a nearly-empty patch in DSP terms. Downgrade that lead accordingly.

**This is a two-point linear fit, not a measurement**, and it assumes DSP
scales with rate while overhead does not. The confirming datum is cheap:
`demo-pd` at 22.05 kHz should land near **33%**. Not taken, because it means
switching patches away from what Bob was listening to.

## Trades this buys, both untested

- **Bandwidth**: Nyquist is now 11 kHz; the top octave is gone.
- **Latency**: 1024 frames at 22.05 kHz is a 46 ms period and ~93 ms buffer,
  about 4x the previous 23 ms. This lands directly on **two-device forward-sync
  timing, which `44/5-pd-adoption` tied without ever measuring on hardware**.
  Whoever runs that rig check should do it at the rate the fleet actually runs.
- With ~40% headroom now, **512 frames at 22.05 kHz** would halve the latency
  back and probably still hold. Untried.
