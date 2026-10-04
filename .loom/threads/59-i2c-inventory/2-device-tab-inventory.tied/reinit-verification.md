# Per-module Re-init — verification

2026-10-04. Worktree `.worktrees/59-2-reinit`, branch `stitch/59-2-reinit`,
based on `607badd` (current main including the stream port). Implements Bob's
ratification in proposal §8d. This completes the remaining Re-init action in
59/2; module values and Monitor panels remain their own stitches.

## Behavior

- Exact UID `io-reinit <name>` returns `/os/io-reinit <uid> <ok|err>` with
  exactly `{name,error}`. No type/address is accepted from the caller.
- The bridge reads the active manifest, rejects undeclared modules, retires
  only the target and runs its setup under the existing IO lock. Other
  instances and registry rows are unchanged. Local success sends the registry
  then `/io/reinitialized <name>` to both 7771 and 6662; failure uses the
  existing `/io/error` vocabulary. Missing hardware stays missing; retirement
  or setup failure is errored; success clears the target's old error.
- Writes and repairs share one node mutation FIFO, preserving one owner for
  a matching terminal error. Repairs bypass the development write gate;
  entering Performance removes queued writes and keeps queued repairs. Late
  write acknowledgments cannot complete repairs, or vice versa. An unrelated
  `write-failed` notification is relayed but does not complete a repair.
- The existing three-second silent node and four-second dashboard deadlines
  are retained. Dashboard pending/receipt/timeout state is per module; duplicate
  pending requests are suppressed, and receipts refresh the report.
- Device rows offer Re-init, disabled offline/pending or for undeclared
  modules. It remains usable in Performance. Timeout and failure feedback
  appear in the target row. Names and errors remain escaped; the existing
  unrelated-form focus guard continues to work.
- Simfleet uses the active manifest, fake bus presence and existing reasons
  to model success/failure without touching other module rows.
- OSC-CONTRACT §6, §11 and §15 and current glean guidance are updated.

## Checks

- Fast suite: **520 tests passed**, including 11 new Re-init tests for FIFO
  attribution, queued repairs in Performance, silent timeout, malformed names,
  target retirement, active-manifest metadata, missing bus/chip, setup/cleanup
  failure, other-instance preservation, dashboard routing and simfleet parity.
- Focused Device IO browser journey: **passed** with real dashboard/simfleet.
  Checks success and missing-chip failure in Performance, active-manifest
  declaration changes without restart, undeclared-button disablement, duplicate
  prevention, timeout/retry, offline disablement, preserved module health and
  existing scan/error/focus behavior.
- Full browser suite: **32/32 verifiers passed**. Its existing localhost IO
  journey now includes a real node/bridge repair receipt
  and registry update while writes are disabled (chip setup is faked).
- `BOPOS_DEVICE_IO_SCREENSHOT` refreshed all four tracked
  `device-io[-dark]-{1440,420}.png` screenshots in this stitch. All four were
  visually inspected; button/state/feedback rows fit, warnings remain legible,
  and the card clears the fixed Monitor dock in both themes and widths.
- `node --check dashboard/static/js/device-io.js` and `git diff --check`: pass.
- Glean index regenerated. No `.pd` edit, push, merge or loom command.

## Operator strings

- `Re-init` (ratified action label).
- `Re-init {module name}` (button accessible label).
- `Re-init timed out. Try again.`
- `Re-init: {existing IO reason}`

The warning glyph and error reason words are reused. No new reason token,
confirmation dialog or other operator action is introduced.

## Hardware pending

No physical Pi, I2C chip or audio was exercised. Real chip cleanup/setup,
recovery after disconnect/reconnect, behavior of shared bus/address aliases,
and continued audio/other-module polling during repair remain hardware checks.
Socket, mock-chip and simfleet results establish software behavior only.
