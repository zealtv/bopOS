# Pi checks for Bob

Fixture tests on macOS cover failed run context, failed `record-active`, immediate
engine exit, successful Pd/generic launches, cleanup ownership, patch start
failure and JACK failure. No real JACK, engine, installer or Pi was run.

- Launch a valid patch on a Pi; verify JACK and the engine remain alive, their
  PID records match, the run context arrives and audio plays. Launch now waits
  one second to catch immediate engine death; this does not prove readiness.
- Apply a working audio configuration, then one that prevents engine startup.
  Verify apply detects failure, the partial launch stops, rollback restores
  the previous configuration and audio resumes.
- With controlled failing run-context/record-active commands and an engine
  entrypoint that exits immediately, verify non-zero launcher status, no
  surviving processes from that launch and no stale records from it. Confirm
  the node/IO services and unrelated processes remain alive.
- Boot with an invalid manifest; verify the existing full-stack skip keeps
  node/IO online, while an engine-only launch still fails.
