# 1-pd-binary-resolution

Stop hardcoding one exact Pd build. Resolve the Pd executable at run time, and
fail loudly and by name when there isn't one.

## What ships today

`tools/audition.py:863-865`:

```python
parser.add_argument("--pd-bin", default=(
    "/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd"
    if sys.platform == "darwin" else "pd"))
```

`dashboard/server.py:3125-3132` never passes `--pd-bin`, so on macOS that
literal is the whole story for the editor. Same for `start_simulation`
(`server.py:3019+`). The Linux branch is already fine — a bare `pd` resolves
through `PATH` in `Popen`.

## The change

1. **A resolver, not a literal.** On darwin: glob `/Applications/Pd-*.app`,
   parse the `MAJOR.MINOR-PATCH` tail, pick the **highest** version whose
   `Contents/Resources/bin/pd` is an executable file. Fall back to
   `shutil.which("pd")`, then to a Homebrew path if you find one worth naming.
   On Linux keep `shutil.which("pd")`. Everywhere: an explicit `--pd-bin` wins
   outright and is never second-guessed.

   Sort on the parsed integer tuple, not the string — `Pd-0.56-2` must beat
   `Pd-0.9-1` and `Pd-0.55-10` must beat `Pd-0.55-2`, both of which a
   lexicographic sort gets backwards. Bob's machine has `0.55-0` and `0.56-2`;
   the right answer there is `0.56-2`.

2. **Preflight in `start_engines`.** `tools/audition.py:224-247` should check
   the resolved binary is an executable file *before* the loop and raise a
   named error — the path it tried, and the candidates it saw. Right now a
   missing binary is a bare `FileNotFoundError` from `Popen` at `:246`, inside
   `run()`'s `except`-less `try/finally` (`:817-819`).

3. **Do not paper over `--no-engine`.** `start_engines` returns immediately when
   `args.no_engine` is set (`:225-226`), and the headless browser suites depend
   on that (`--sim-no-engine`, per CLAUDE.md's testing notes). The resolver must
   not run, and must not fail, on that path — no Pd is *correct* there.

## Verify

- Unit-level, browser-free, in `tests/`: the version sort, "explicit `--pd-bin`
  wins", "no candidates resolves to `None` rather than a literal", and the
  named preflight error. Feed it a fabricated `/Applications`-shaped tmpdir —
  do not assert against whatever Pd the developer's machine happens to have,
  or the test asserts the machine rather than the code. Put it where the code
  surface lives, per the tied `27-tied-guard-rot` two-tier split.
- On the affected machine: *Launch editor* opens Pd, with `#editor-status`
  reaching and holding `running`.
- Then remove the stopgap symlink if one was made
  (`/Applications/Pd-0.55-2.app` → the real bundle) and confirm it still works.
  That symlink existing is the exact condition under which this stitch can pass
  while changing nothing.

## Carry forward

`.loom/legacy-v1/tied/pe-2-edit-mode/verify_pe2_edit_mode.py:128-130` skips its
real GUI-PD launch when `pd_bin` is not executable, by calling
`audition.parse_args([]).pd_bin` — the same default. It has therefore been
self-skipping on every machine without that one build, reporting green. It is
an archived record and **not** ours to repair (CLAUDE.md is explicit that the
archive is evidence, not a regression suite). Note it in `decisions.md` as the
first, unread instance of this bug rather than fixing it.
