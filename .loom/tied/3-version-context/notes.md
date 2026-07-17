# 3-version-context — notes

Delivers `version` and `patch_fingerprint` in the launch-delivered run
context, per the ratified design in `1-contract-amendment` (tied,
`2ee746b`).

## What changed

- `python/runcontext.py`:
  - `resolve_version(repo_dir=None)` — `git rev-parse --short HEAD`,
    degrading to `"unknown"` on any failure (same shape as
    `bopos.py:resolve_version()`, kept as a small self-contained copy here
    rather than importing all of `bopos.py`'s heavier machinery into the
    lightweight launch-time CLI).
  - `resolve_patch_fingerprint(patch_path)` — nonblocking: uses
    `identity.cached_directory_info(patch_path)`, the same never-hashes fast
    path the asset inventory already uses, returning the cached fingerprint
    only when the walk is fully warm, else `"unknown"`. Also guards a
    missing/nonexistent `patch_path` explicitly — `cached_directory_info` on
    an empty/absent walk otherwise reports the *empty-manifest* fingerprint
    as if `complete` were trivially true, which would be a wrong answer, not
    an honest "unknown". No patch launch ever triggers synchronous hashing;
    a real fingerprint appears only after something has warmed that
    directory's cache in the background (nothing does that for patches yet
    — see "not done" below).
  - `generate()` now returns `version` and `patch_fingerprint` alongside the
    existing `seed`/`run_id`, and takes optional `repo_dir`/`patches_dir` so
    callers whose patch lives outside `<repo>/patches/<name>` (audition) can
    still resolve the right directory.
  - `main()` (the CLI launchers `eval`) prints two more lines:
    `BOPOS_VERSION=` / `BOPOS_PATCH_FINGERPRINT=`.

- Launchers updated in the same atomic launch step (grepped `bopos-context`,
  `-send`, `BOPOS_SEED` across `bash/` and `tools/` per the instructions):
  - `bash/start-engine.sh` — PD gets two more `bopos-context` sends; other
    engines get `BOPOS_VERSION`/`BOPOS_PATCH_FINGERPRINT` in their env line.
  - `bash/start-laptop.sh` — PD `-send` string extended the same way.
  - `tools/perf_matrix.sh` — same PD `-send` extension (mirrors
    `start-engine.sh` per its own comment).
  - `tools/audition.py` — `engine_command`'s PD startup string and
    `start_engines`'s non-PD env dict both extended; both call sites now pass
    `patches_dir=os.path.dirname(patch_dir)` to `runcontext.generate()` so
    fingerprint resolution uses the manifest's real directory (audition
    patches aren't guaranteed to live under `<repo>/patches/`).

- `tools/simfleet.py`: run context is delivered only at engine *launch*,
  and simfleet never launches an engine process — it answers the LAN wire
  (5550/6660) for N devices sharing one process, with no
  `subprocess.Popen`/`.run` anywhere and no `bopos-context` bus to write to.
  There is nothing for it to mirror here; noted per the instructions rather
  than adding an unmotivated stub. (Separately, in the course of this
  sweep, bumped simfleet's *unrelated* fake `/os/report` `contract_version`
  literal from `"1.6"` to `"1.7"` for version parity with the real
  `bopos.py`, which stitch 2 already moved to 1.7 — a stale-version
  cleanup in the same spirit as the CLAUDE.md/README.md sweep in stitch 1,
  not a run-context change.)

- Did not touch any `.pd` file — PD receives the two new items purely via
  the existing `bopos-context` `-send` bus; patches just add
  `[route version patch-fingerprint]` on their own schedule, per the
  contract amendment.

## Design choices made without further ratification

- Patches have no background cache-warming pass analogous to
  `warm_asset_cache`/`initialise_asset_cache` for assets. This stitch does
  not add one — the instructions only asked to reuse the existing fast path
  and fall back to `"unknown"`, and adding a patch-cache warmer is a
  separate, non-trivial design (when to warm, for which patch, at what
  priority) that Bob didn't ask for here. Recorded honestly: in practice,
  `patch_fingerprint` will read `"unknown"` at every launch today unless
  something else (e.g. an `/os/patches` query, which calls
  `identity.fingerprint` directly and synchronously warms the shared
  in-process cache as a side effect) has already warmed that patch's
  directory in this process's lifetime. This is consistent with "never
  block launch on hashing" and is the smallest reasonable choice given the
  instructions' explicit "if no fast answer exists, deliver unknown."

## Verification

`verify_version_context.py` (browser-free, run with
`~/.venvs/bopos/bin/python`) — 28/28 checks pass:

- `runcontext.generate()` still returns `seed`/`run_id` and now also
  `version`/`patch_fingerprint`, both strings.
- `resolve_version` matches a real `git rev-parse --short HEAD` against this
  checkout, and degrades to `"unknown"` when pointed at a non-git temp dir.
- `resolve_patch_fingerprint` returns `"unknown"` for `None` and for a
  nonexistent path (proving the empty-manifest-hash trap is guarded).
- Builds a real temp patch directory: confirms an unwarmed cache answers
  `"unknown"` (never hashes), then calls `identity.warm_hash_cache` (the
  same mechanism the asset inventory's background warm uses) and confirms
  the now-warm cache answers a real 64-hex fingerprint matching
  `identity.fingerprint`'s direct hash.
- Confirms neither string ever parses as a Python float (PD 32-bit float
  house rule).
- Confirms `generate(..., patches_dir=...)` resolves a patch living outside
  `<repo>/patches/`, matching audition's call pattern.
- Regex-greps each launcher (`start-engine.sh`, `start-laptop.sh`,
  `perf_matrix.sh`, `audition.py`) for the exact new `bopos-context`/env-var
  wiring, and confirms `simfleet.py` still launches no engine process (i.e.
  the "nothing to mirror" claim above stays true rather than silently going
  stale).

Ran: `~/.venvs/bopos/bin/python .loom/threads/patch-admin-surface/
3-version-context.stitching/verify_version_context.py` — `28/28 passed`.

## Honestly out of scope / not verified here

- Real Pi launch (`bash/start-engine.sh` end to end with real `jackd`/`pd`)
  was not run — this is hardware/engine verification needing a live rig or
  Bob; only the Python-level context generation and shell-script wiring were
  exercised.
- The PD-side `[route version patch-fingerprint]` consumption inside a real
  patch is Bob's `.pd` follow-up, per house rules; nothing on the PD side
  was touched or can be exercised without a `.pd` edit.
