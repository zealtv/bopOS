# Clock-sync jitter — sim baseline

Generated 2026-07-09 22:52:47 by `tools/sync_measure.py`.

> **Loopback / single-process floor, not the deliverable.** All sim
> devices share one machine's `CLOCK_MONOTONIC` and one event loop, so
> the spread below is the software floor. The real number is the
> hardware run (`sync-4`): N Pis on WiFi, fire evidence recorded
> externally. Target there: <10 ms typical spread.

## Run

- devices: 5   skew: ±40.0 ms   jitter: 2.0 ms   cues: 8
- sync settle: 4.0s   cue lead: 500.0 ms   gap: 250.0 ms

## Cross-device cue spread

- **max spread:** 1.007 ms
- **typical (median) spread:** 0.874 ms
- cues measured: 8 / 8

| cue | devices | spread (ms) |
|---|---|---|
| m0 | 5 | 0.734 |
| m1 | 5 | 0.876 |
| m2 | 5 | 0.982 |
| m3 | 5 | 1.007 |
| m4 | 5 | 0.868 |
| m5 | 5 | 0.920 |
| m6 | 5 | 0.872 |
| m7 | 5 | 0.846 |

## Per-device offset estimate

| id | uid | offset (ms) |
|---|---|---|
| 1 | 02:53:49:4d:00:01 | 24.060 |
| 2 | 02:53:49:4d:00:02 | 34.588 |
| 3 | 02:53:49:4d:00:03 | 14.868 |
| 4 | 02:53:49:4d:00:04 | -31.326 |
| 5 | 02:53:49:4d:00:05 | -5.809 |

