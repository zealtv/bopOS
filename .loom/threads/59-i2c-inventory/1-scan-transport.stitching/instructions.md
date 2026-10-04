# 1-scan-transport: IO control path

**Status:** ready (0a ratified 2026-10-04)
**Goal:** the control path from the io bridge to the dashboard that `2`–`9` ride on.

Spec: `../0a-io-design-review.tied/proposal.md` (ratified 2026-10-04; Bob's words in `rulings.md`). Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit. Wire changes are ratified as written in proposal §8; write the matching contract text and §15 row as each piece ships.

- Bridge replies go to 6662 (unchanged) **and** to `bopos.py` on new localhost
  **7771** (proposal §1). `bopos.py` sends commands to the bridge on 8880.
- Admin verbs `io-scan`, `io-write` (§8, payloads §8a; `io-modules` dropped); unsolicited
  `/os/io-error <uid> <name> <reason>`.
- Error vocabulary: `no-bus`, `create-failed`, `invalid-arguments`,
  `unknown-command`, `write-failed`; reserved name `bridge`. This replaces the
  log-only diagnostics from `67-repair-pass/3-io-bridge-hardening`; update that
  stitch's notes.
- `/os/report` gains `io: {bus, scanned, modules: {…}}`.
- simfleet: a configurable fake bus and modules (replacing `"has_i2c": False`).

## Settle while building (carried from the old stitch)

- **"No bus" ≠ "empty bus" ≠ "not scanned".** Never let blank mean "nothing attached".
- **Bus number:** fixed at 1, or a parameter? Say why.
- The scan runs in the bridge (it skips live peripherals). Contention is
  measured on the rig only if that ever changes.
