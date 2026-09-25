# clock-sync

**Goal:** a forward-synchronised clock across the fleet, so events fire
near-simultaneously over Wi-Fi, engine-agnostically.

**Status:** mechanism built and tied (`sync-0`..`sync-3`, in
`.loom/legacy-v1/tied/`). Only the hardware measurement is left
(`sync-4-hw-measurement`, needs rig).

**Done when:** N Pis on installation Wi-Fi fire an audible click within budget
(**< 10 ms typical**), with a recorded measurement.

## How it works (reference)

Happy Brackets-style (`lore:2026-09-25-architecture-review-2026-07-05` §5):

- The **dashboard is the clock leader** (Bob, 2026-07-05). Pings, nodes
  (`bopos.py`, `python/sync_node.py`) reply, offsets are smoothed.
- Events carry a shared time: `/e/<id> <sharedTime …>` (contract v1.14; the old
  `/cue` plane was retired in v1.15). The node converts to a local monotonic
  deadline and fires the event to the engine then.

Rules that still bind:

- **Pd never sees absolute time** (32-bit floats) — 64-bit times travel as
  strings/int pairs.
- `time.monotonic()` on nodes, never wall clock.
- Slew corrections while audio runs; never step.
- Jitter ping intervals to avoid lockstep bursts.

## Note for the measurement

Finn Jet now runs 32 kHz / 1024-frame buffers (see
`pi-zero-performance/measurements-2026-08-13-finn-jet.md`) — much more latency
than the old defaults. Measure at the rate the fleet actually runs.
