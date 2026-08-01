# 1-contract-amendment — notes

Doc-only stitch. Amended `docs/OSC-CONTRACT.md` v1.6 → v1.7:

- Header version bumped to 1.7, latest-revision date to 2026-07-17.
- §4.2 engine-sent surface (localhost 7770): softened the "requests only —
  administrative commands never cross" sentence to name the bounded
  exception, and added `/admin <action>` (`update-patch`, `update-bopos`,
  `shutdown`, `reboot`) with the no-selector/no-reply/unknown-ignored
  behaviour from the instructions, verbatim in spirit.
- §4.2 PD paragraph: added a note that the PD-side `/admin` bus plumbing
  (e.g. `to-bopos-admin` in `pd/bopos.pd`) is not yet wired — that's Bob's
  patch edit, per house rules.
- §4.2 run-context paragraph: added `bopos-context version <string>` /
  `bopos-context patch-fingerprint <string>` for PD and `BOPOS_VERSION` /
  `BOPOS_PATCH_FINGERPRINT` for other engines, both additive strings (PD
  32-bit float rule cited inline).
- §15 revision history: added the `1.7 | 2026-07-17` changelog row pointing
  at `.loom/tied/1-contract-amendment/` as the decision record.
- Swept `docs/*.md`, `CLAUDE.md`, `README.md` for stale `v1.6`/`1.6`
  contract-version prose and bumped the ones that name "the current
  version" (CLAUDE.md §Start-here pointer, CLAUDE.md Thread-ordering
  foundation-status paragraph, README.md Status line). Left the §7
  `optional outcome additive in v1.6` mention alone — that's a correct
  historical fact about when that feature landed, not a "current version"
  claim.
- Did not touch `python/bopos.py`'s reported `contract_version` — that's
  explicitly deferred to stitch 2.

## Verification

Doc-only stitch, no code path to execute. Verification consisted of:

1. Proofreading the rendered markdown by re-reading the edited sections
   (§4.2, §15) in full after editing.
2. `grep -rn "1\.6" docs/*.md CLAUDE.md README.md` before and after the
   edit to confirm every stale "current version" mention was caught, and
   that the one remaining `v1.6` hit (§7's dated "additive in v1.6" note)
   is a correct historical reference, not a stale current-version claim.
3. Markdown sanity check: the amended code fences render as valid fenced
   blocks (opening/closing triple-backtick count is even) and the new
   table row matches the existing `| version | date | change | record |`
   column shape.

No hardware, PD, or Python surface was touched, so there's nothing further
to run from the `~/.venvs/bopos` venv for this stitch.
