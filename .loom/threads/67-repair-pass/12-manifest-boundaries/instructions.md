# 12-manifest-boundaries

**Status:** ready
**Goal:** the manifest validator and CLI hold their boundary: bad values are
rejected as errors, accepted values reach the launcher as literal data and the
wire as representable scalars.

Evidence: `lore:2026-10-05-bopos-review-core-libs` F1, F2, F3 (with `reproduce.py`).

- **F1 (high).** `manifest.py` CLI single-quotes engine/entrypoint values
  without escaping; `start-engine.sh` evals them. Quote correctly
  (`shlex.quote`) or replace the eval handoff — simpler wins.
- **F2.** `kind: []`, NUL entrypoints and `10**400` defaults raise instead of
  returning `(None, error)`.
- **F3.** Float defaults beyond float32 and ints beyond int32 validate, then
  can't be sent. Reject them; same for plain numeric generator values. No new
  public limits without ratification.

Done when: each fails before the fix and passes after; fast green.
