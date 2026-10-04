# Performance mode verification

Worktree: `/Users/bob/repos/bopOS/.worktrees/77-performance-mode`, branch
`stitch/77-performance-mode`. Ratified source: `59/0a` proposal §2/§8 and
its rulings. No Pure Data edits, push, merge or loom lifecycle commands.

## Implementation

- Host-global `performance.json` and node `state/performance.json`: atomic,
  fsync-backed writes only on change, default development, independent of
  project and ephemeral engine stores. No expiry or locked exit.
- `/all/os/performance <0|1>`; existing uid-bearing `/os/report` confirms the
  boolean. Host convergence on discovery/reappearance, report disagreement,
  and bounded retries on heartbeats while unconfirmed.
- Device gates for probes, Wi-Fi, patch fetch/switch/removal; pending patch
  work rechecks under the same lock as the mode transition. An in-flight
  patch mutation finishes before the node acknowledges Performance.
- `bopos.development_allowed(operation, state)` is the integration point for
  later `io-stream`, `io-write`, and `stream-to-editor` handlers. Streaming
  producers must check it while sending, as well as when accepting a lease.
  Those features are not built here.
- Host blocks stale/forged development requests; matching UI controls are
  disabled, Patch Edit closes on entry, and the toggle always remains enabled.
  Simulation and show-time audio controls remain separate.
- Structured `/log` and both service stdout/stderr sinks route to Linux
  `/dev/shm` tmpfs in Performance, or bounded memory on hosts without tmpfs.
  Prior structured files close under the append lock before mode changes.
  Service sink RAM failures fall back to memory without breaking stdout.
  Configured internal/USB destination is retained, effective report is `ram`.
  RAM logs never copy to persistent storage on leaving Performance.
- Contract v1.21 documents this ratified subset; no new ports or log-content
  stream. Merge the other additive v1.21 IO contract amendment from 59/1.

## Software checks

- `./tools/run-tests.sh fast`: **460 tests passed** (includes 17 focused
  Performance tests). Expected fault-injection diagnostics are printed.
- `~/.venvs/bopos/bin/python tests/test_performance_mode.py`: persistence,
  never-locked exit, operation predicate, actual node dispatch refusals,
  queued-work recheck, host restart/project independence, stale-tab gates,
  convergence, RAM routing, concurrent append exclusion, RAM sink failure,
  and simulator parity.
- `BOPOS_PERFORMANCE_SCREENSHOT=<scratchpad> ~/.venvs/bopos/bin/python
  tests/verify_performance_mode.py`: **passed** against real dashboard and
  simfleet, including contradictory node assertions restored by the host,
  both host and node restarts, locks/unlocks and an existing editor closing.
- `./tools/run-tests.sh browser`: **all 29 journeys passed**. Complete log
  retained as `browser-77.log` in the task scratchpad. After that run, the
  focused journey also verified that a known mode disagreement remains
  visible when its device goes offline.
- Every changed Python file compiled via `python -m py_compile`, with
  `PYTHONPYCACHEPREFIX=/private/tmp/bopos-performance-pycache`.
- `node --check` passed for dashboard, Monitor and Wi-Fi JS; `git diff
  --check` passed.
- Six screenshots in the task scratchpad:
  `performance-{on,off}-{1440,900,420}.png`, viewport height 900. Inspected
  desktop and narrow layouts. Header wraps earlier to retain long project,
  Site, Patch and Show names alongside the new prominent toggle.

## Pending hardware checks

No Pi, real I2C peripheral, real audio engine, installation-LAN broadcast,
iPad or hard power cut was exercised. Do not call those verified.

On Finn Jet / Ciro Toast, confirm remembered mode across a hard shutdown,
actual `/dev/shm` placement and SD log cessation (including buffering,
stdout sinks, engine `/log`, old open handles and shutdown). Check the
physical patch/Wi-Fi/probe refusals, always-available exit, and live audio
control continuity. This is a logging mode, not a read-only filesystem:
the intentional mode write and existing non-log state writes remain.

## Regression findings

The first browser sweep found three issues, corrected before completion:
one legacy physical-peer fixture omitted the new boolean and caused
background convergence during an unrelated no-command assertion; long
project names needed the header to wrap sooner; and browser report
enrichment could coalesce a short-lived disagreement before rendering.
The disagreement journey now verifies the actual simulated node mode files
change and are restored, avoiding a vacuous browser-only assertion.
