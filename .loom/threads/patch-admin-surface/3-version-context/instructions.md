# 3-version-context

Deliver bopOS version and active-patch fingerprint to engines in the
launch-delivered run context, per the `1-contract-amendment` ratification
(must be tied first).

## Design (pinned)

- PD: two more `bopos-context` messages at launch — `version <string>` and
  `patch-fingerprint <string>`. This rides the existing `-send` bus, so no
  `.pd` edits are needed; patches just `[route version patch-fingerprint]`.
- Other engines: `BOPOS_VERSION` and `BOPOS_PATCH_FINGERPRINT` environment
  variables, alongside the existing `BOPOS_SEED`/`BOPOS_RUN_ID`/…
- Strings end-to-end. Fingerprint falls back to the literal `unknown` when
  it cannot be resolved quickly at launch — launching must never block on
  hashing.

## Where to look

- `python/runcontext.py` — generates seed/run-id and prints eval-able env
  lines for the launchers. Extend it (or the launcher) to resolve version
  and fingerprint. Version resolution already exists in
  `python/bopos.py: resolve_version()`; fingerprints via
  `python/identity.py`'s `fingerprint(path)` and the cached inventory in
  bopos.py (`installed_patches`). Prefer reusing the cache/fast path;
  do not re-hash a large patch synchronously at every launch — if no fast
  answer exists, deliver `unknown`.
- Find the actual engine launcher(s) (grep `bash/` and `python/` for
  `bopos-context`, `-send`, `BOPOS_SEED`) and add the two items in the same
  atomic launch step. Audition/preview launches (`tools/audition.py`) should
  stay consistent — check how they build context and mirror it.

## Parity + verification

- simfleet: if it models run context at all, mirror the addition; if not,
  note that in the stitch.
- `verify_*.py` in the stitch directory (browser-free): assert the launcher
  context now contains both items, and that a missing fingerprint degrades
  to `unknown` rather than blocking or crashing. Repo located by marker;
  run with `~/.venvs/bopos/bin/python`.
