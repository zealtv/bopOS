# Merge integration verification — 2026-10-04

Main checkout `/Users/bob/repos/bopOS`, HEAD `da80c75`, pending merge source
`c908bf0` (`stitch/77-performance-mode`). Resolved and staged, uncommitted.
The original worktree verification remains in `verification.md`.

Ratified source: `59-i2c-inventory/0a-io-design-review.tied/proposal.md` §8b.
`performance` is the administrative IO write refusal, never a module fault.

The node's IO controller checks `development_allowed` at admission and before
each queued bridge send. Mode entry and bridge sends share the IO lock;
entry immediately rejects waiting writes without disturbing attribution of
the already-sent head. Exit does not replay rejected work. Scans stay allowed.
Dashboard receipt validation and simfleet retain the distinction between an
administrative refusal and a peripheral error. The merged v1.21 contract and
port reference document the shipped subset and pending streaming work.

- Fast suite: **484 passed**, exit 0, including six added IO integration tests
  and concurrent mode-entry/bridge-send exclusion.
- Browser suite: **30 journeys passed**, exit 0, including real dashboard /
  simfleet Performance IO refusal, healthy module, scan and exit behavior;
  localhost bridge/node IO uses faked chip access.
- Staged diff check passed; no unmerged index entries or staged `.pd` edits.
- Corrected the existing failed-load fixture's project path to stay inside
  its temporary root; the intended malformed-project assertions pass.

Complete report and logs: task scratchpad `report-merge77.md`,
`fast-merge77.log`, `browser-merge77.log`.

No physical Pi/I2C/audio, hard shutdown, or actual SD-write cessation checks.
No commit, push, or loom lifecycle change was made.
