# Runner contract for child 07

Implement one repository-root entry point:

```sh
./tools/run-tests.sh [fast|browser|all]
```

## Required behavior

- Default to `fast` when no tier is supplied.
- Resolve Python from `BOPOS_PYTHON` when explicitly set; otherwise use
  `~/.venvs/bopos/bin/python` and fail with the existing setup guidance if it is
  absent.
- Set `PYTHONDONTWRITEBYTECODE=1`.
- `fast` runs:

  ```sh
  python -m unittest discover -s tests -p 'test_*.py'
  ```

- `browser` discovers `tests/verify_*.py` in lexical order and runs each in a
  fresh process from the repository root. Continue through failures and print a
  final per-file pass/fail summary so one failure does not hide later surfaces.
- `all` runs `fast`, then `browser`, and returns nonzero if either tier fails.
- Validate the tier argument and provide concise usage.
- Never discover or execute `.loom/tied/`.
- Do not include hardware, Pure Data, audible, real-LAN, or iPad adoption checks
  in a software pass.
- Preserve verifier output; use temporary logs only if they are always cleaned
  up.

There is no repository CI workflow as of this inventory. Child `07` should add
the runner and document it as the pre-tie command. It should wire the fast tier
into actual CI only if a real repository CI surface exists by then; this stitch
does not authorize inventing an external service or credentials.

The shell entry point is preferred over a new Python framework because it only
orchestrates two already-established Python invocation styles and keeps
dependency tiers visible.
