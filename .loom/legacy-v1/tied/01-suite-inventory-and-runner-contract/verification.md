# Verification

## Checks performed

Living-suite file inventory:

```sh
rg --files tests | sort
```

Result: 27 Python files — 15 `test_*.py` modules and 12 `verify_*.py`
standalone browser journeys.

Fast-suite discovery:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py' -v
```

Result: **99 tests passed** in 0.156 seconds.

Archive inventory:

```sh
rg --files .loom/tied |
  rg '/(verify|test)[^/]*\.py$' |
  sort
```

Result: 189 Python guard files. They were enumerated and searched for migration
candidates only; none were executed, copied, repaired, or modified.

Repository runner/CI search:

```sh
rg --files |
  rg '(^|/)(test|verify|check|ci|run-tests)(\.sh|\.py|\.yml|\.yaml)$|Makefile|pyproject.toml|pytest.ini|tox.ini'
test ! -d .github
find . -maxdepth 2 -type f \
  \( -name Makefile -o -name pyproject.toml -o -name pytest.ini \
     -o -name tox.ini -o -name '*test*.sh' -o -name '*tests*.sh' \)
```

Result: no checked-in aggregate runner, test configuration, or CI workflow.

## Limitations

No Playwright journey was run because this planning stitch changes no behavior
and only defines the slower tier. No hardware, Pure Data, audible output, LAN,
peripheral, or iPad behavior was tested.
