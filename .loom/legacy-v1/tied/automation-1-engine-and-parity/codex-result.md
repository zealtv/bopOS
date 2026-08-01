Implemented the parameter automation engine, bopos wiring, simfleet parity, and focused verifier.

- Focused verifier: 32 checks passed.
- Two parameter/protocol regressions passed.
- Python compilation and `git diff --check` passed.
- The mandated framework-slimdown verifier remains blocked by sandbox UDP restrictions and contains a pre-existing stale `/admin` expectation. It was not amended.
- No dashboard, `.pd`, or Loom state files were touched. No commit made.

Full results: [codex-report.md](/Users/bob/repos/bopOS/.loom/threads/16-param-automation/automation-1-engine-and-parity.stitching/codex-report.md)