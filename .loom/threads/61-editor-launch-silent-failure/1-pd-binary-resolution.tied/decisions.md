# decisions — 1-pd-binary-resolution

- **The default is gone, not replaced.** `--pd-bin` now defaults to `None` and
  resolution happens at run time in `resolve_pd_bin()`. An explicit `--pd-bin`
  is returned untouched and never second-guessed, as instructed.
- **Resolution order on darwin:** highest `/Applications/Pd-MAJOR.MINOR-PATCH.app`
  whose `Contents/Resources/bin/pd` is an executable file → `shutil.which("pd")`
  → `/opt/homebrew/bin/pd`, `/usr/local/bin/pd`. Elsewhere: `shutil.which("pd")`
  only. Sorting is on the parsed integer tuple, so `0.56-2` beats `0.9-1` and
  `0.55-10` beats `0.55-2`.
- **A non-executable bundle is skipped, not fatal.** A half-installed newer Pd
  therefore falls through to the working older one rather than failing the run.
- **Preflight sits in `start_engines`, gated on the engine actually being pd.**
  `--no-engine` returns before it (verified by a test that makes both
  `pd_binary()` and `_load_patch()` explode), and an `--engine-command` override
  or a non-pd engine never resolves a Pd binary it will not use.
- **`AuditionRig.pd_binary()` caches**, so the N-node loop resolves once and
  `engine_command` reads the same value for every node.
- **Not ours to repair, recorded instead:**
  `.loom/legacy-v1/tied/pe-2-edit-mode/verify_pe2_edit_mode.py:128-130` calls
  `audition.parse_args([]).pd_bin` and skips its real GUI-PD launch when that
  is not executable. That is the **first, unread instance of this bug** — a
  tied guard quietly self-skipping on every machine without one exact build and
  reporting green. The archive is evidence, not a regression suite (CLAUDE.md),
  so it stays as-is. Note that with the new `None` default it now skips by a
  different route rather than a stale path; either way it does not run.
- **`dashboard/server.py` is unchanged.** It never passed `--pd-bin`, which is
  now the correct behaviour rather than the bug: the resolver owns the choice,
  for the editor supervisor and `start_simulation` alike.
